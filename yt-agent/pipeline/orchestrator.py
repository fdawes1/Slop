from __future__ import annotations
import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

import anthropic
from rich.console import Console
from rich.panel import Panel

from models import PipelineState, Script, Section, VideoMetadata
from pipeline.state import save_state, load_state
import agents.strategy_agent as strategy_agent
import agents.research_agent as research_agent
import agents.script_agent as script_agent
import agents.seo_agent as seo_agent
import agents.voice_agent as voice_agent
import agents.video_agent as video_agent
import agents.thumbnail_agent as thumbnail_agent
import agents.upload_agent as upload_agent
import agents.analytics_agent as analytics_agent

console = Console()


def run_pipeline(
    channel_config: Dict,
    settings: Dict,
    env: Dict,
    topic_override: Optional[str] = None,
    dry_run: bool = False,
    resume_run_id: Optional[str] = None,
) -> PipelineState:
    client = anthropic.Anthropic(api_key=env["ANTHROPIC_API_KEY"])
    output_dir = settings["paths"]["output"]
    data_dir = settings["paths"]["data"]
    Path(output_dir).mkdir(exist_ok=True)
    Path(data_dir).mkdir(exist_ok=True)

    if resume_run_id:
        state = load_state(resume_run_id, data_dir)
        if not state:
            raise RuntimeError(f"Run {resume_run_id} not found")
        console.print(f"[yellow]Resuming {resume_run_id} from: {state.status}[/yellow]")
    else:
        state = PipelineState()
        console.print(f"[dim]Run ID: {state.run_id}[/dim]")

    try:
        # ── Phase 1: Topic selection ──────────────────────────────────────────
        if state.status == "initialized":
            console.rule("[bold blue]Phase 1: Research & Strategy")

            if topic_override:
                state.topic = topic_override
                state.angle = "comprehensive analysis"
                console.print(f"[green]Topic: {topic_override}[/green]")
            else:
                console.print("[cyan]Scraping trending topics...[/cyan]")
                trending = research_agent.gather_trending_topics(channel_config)
                console.print(f"[dim]Found {len(trending)} topics[/dim]")

                history = _load_history(data_dir)
                sel = strategy_agent.select_topic(
                    trending, channel_config, history, client,
                    model=settings["models"]["strategy"],
                )
                state.topic = sel["topic"]
                state.angle = sel["angle"]
                console.print(Panel(
                    f"[bold]{state.topic}[/bold]\n[italic]{state.angle}[/italic]",
                    title="Selected Topic",
                ))

            state.status = "topic_selected"
            save_state(state, data_dir)

        # ── Phase 2: Deep research ────────────────────────────────────────────
        if state.status == "topic_selected":
            console.print("[cyan]Researching topic...[/cyan]")
            research = research_agent.deep_research(
                state.topic, state.angle, client,
                model=settings["models"]["script_writer"],
            )
            _save_json(output_dir, state.run_id, "research.json", research)
            state.status = "researched"
            save_state(state, data_dir)
        else:
            research = _load_json(output_dir, state.run_id, "research.json") or {}

        # ── Phase 3: Script ───────────────────────────────────────────────────
        if state.status == "researched":
            console.rule("[bold blue]Phase 2: Script & Metadata")
            console.print("[cyan]Writing script...[/cyan]")
            script = script_agent.generate_script(
                state.topic, state.angle, research, channel_config, client,
                model=settings["models"]["script_writer"],
                target_duration=channel_config["channel"]["video_format"]["target_duration"],
            )
            state.script = asdict(script)
            state.status = "scripted"
            save_state(state, data_dir)
            console.print(f"[green]Script: {len(script.sections)} sections, ~{script.total_duration:.0f}s[/green]")
        else:
            script = _dict_to_script(state.script)

        # ── Phase 4: SEO metadata ─────────────────────────────────────────────
        if state.status == "scripted":
            console.print("[cyan]Generating SEO metadata...[/cyan]")
            metadata = seo_agent.generate_metadata(
                script, research, channel_config, client,
                model=settings["models"]["seo_optimizer"],
            )
            state.metadata = asdict(metadata)
            state.status = "metadata_ready"
            save_state(state, data_dir)
            console.print(f"[green]Title: {metadata.title}[/green]")
        else:
            metadata = VideoMetadata(**state.metadata)

        # ── Phase 5: Voiceover ────────────────────────────────────────────────
        if state.status == "metadata_ready":
            console.rule("[bold blue]Phase 3: Production")
            console.print("[cyan]Generating voiceover...[/cyan]")
            audio_path, durations = voice_agent.generate_voiceover(
                script, state.run_id, settings["tts"], env, output_dir,
            )
            state.audio_path = audio_path
            _save_json(output_dir, state.run_id, "durations.json", durations)
            state.status = "audio_ready"
            save_state(state, data_dir)
            console.print(f"[green]Audio: {sum(durations):.0f}s[/green]")
        else:
            audio_path = state.audio_path
            durations = _load_json(output_dir, state.run_id, "durations.json") or _estimate_durations(script)

        # ── Phase 6: Images & thumbnail ───────────────────────────────────────
        if state.status == "audio_ready":
            console.print("[cyan]Generating images...[/cyan]")
            image_paths = video_agent.generate_section_images(
                script, state.run_id, settings, env, output_dir,
            )
            console.print(f"[green]{len(image_paths)} images generated[/green]")

            console.print("[cyan]Generating thumbnail...[/cyan]")
            branding = channel_config["channel"].get("branding", {})
            thumb_settings = {**settings, "branding": branding}
            thumb_path = thumbnail_agent.generate_thumbnail(
                script, metadata, state.run_id, thumb_settings, env, output_dir,
            )
            state.thumbnail_path = thumb_path
            state.status = "images_ready"
            save_state(state, data_dir)
        else:
            image_paths = _collect_image_paths(output_dir, state.run_id, script)
            thumb_path = state.thumbnail_path

        # ── Phase 7: Video assembly ───────────────────────────────────────────
        if state.status == "images_ready":
            console.print("[cyan]Assembling video...[/cyan]")

            metadata.description = seo_agent.add_timestamps(
                metadata.description, script.sections, durations[1:-1],
            )

            video_path = video_agent.assemble_video(
                script, image_paths, durations, audio_path,
                state.run_id, settings, output_dir,
            )
            state.video_path = video_path
            state.status = "video_ready"
            save_state(state, data_dir)
            console.print(f"[green]Video: {video_path}[/green]")
        else:
            video_path = state.video_path

        # ── Phase 8: Upload ───────────────────────────────────────────────────
        if not dry_run and state.status == "video_ready":
            console.rule("[bold blue]Phase 4: Upload")
            console.print("[cyan]Uploading to YouTube...[/cyan]")
            youtube_id = upload_agent.upload_video(
                video_path, thumb_path, metadata, env, data_dir,
            )
            upload_agent.save_video_record(state.run_id, state.topic, metadata, youtube_id, data_dir)
            state.youtube_id = youtube_id
            state.status = "uploaded"
            save_state(state, data_dir)
            console.print(Panel(
                f"[bold green]Published![/bold green]\nhttps://youtu.be/{youtube_id}\n{metadata.title}",
                title="SUCCESS",
            ))
        elif dry_run and state.status == "video_ready":
            state.status = "dry_run_complete"
            save_state(state, data_dir)
            console.print(Panel(f"[yellow]Dry run complete.\nVideo: {video_path}[/yellow]", title="DRY RUN"))

        state.status = "complete"
        save_state(state, data_dir)
        return state

    except Exception as e:
        state.status = "failed"
        state.error = str(e)
        save_state(state, data_dir)
        console.print(f"[red]Pipeline failed: {e}[/red]")
        console.print(f"[dim]Resume with: python run.py run --resume {state.run_id}[/dim]")
        raise


# ── helpers ───────────────────────────────────────────────────────────────────

def _load_history(data_dir: str):
    p = Path(data_dir) / "video_history.json"
    return json.loads(p.read_text()) if p.exists() else []


def _save_json(output_dir: str, run_id: str, filename: str, data):
    p = Path(output_dir) / run_id
    p.mkdir(parents=True, exist_ok=True)
    (p / filename).write_text(json.dumps(data, indent=2))


def _load_json(output_dir: str, run_id: str, filename: str):
    p = Path(output_dir) / run_id / filename
    return json.loads(p.read_text()) if p.exists() else None


def _dict_to_script(d: dict) -> Script:
    sections = [Section(**s) for s in d["sections"]]
    return Script(
        topic=d["topic"], angle=d["angle"], hook=d["hook"],
        sections=sections, cta=d["cta"],
        total_duration=d.get("total_duration", 0),
    )


def _estimate_durations(script: Script) -> List[float]:
    wpm = 148
    def dur(text: str) -> float:
        return (len(text.split()) / wpm) * 60
    return [dur(script.hook)] + [dur(s.narration) for s in script.sections] + [dur(script.cta)]


def _collect_image_paths(output_dir: str, run_id: str, script: Script) -> List[str]:
    images_dir = Path(output_dir) / run_id / "images"
    names = ["hook"] + [f"section_{i}" for i in range(len(script.sections))] + ["cta"]
    return [str(images_dir / f"{n}.png") for n in names if (images_dir / f"{n}.png").exists()]
