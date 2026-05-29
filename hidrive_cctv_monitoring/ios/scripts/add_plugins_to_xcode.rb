#!/usr/bin/env ruby
# Adds the custom Swift plugin files to the Xcode project so they are compiled.
# Run from the hidrive_cctv_monitoring/ios/ directory.
require 'xcodeproj'

project_path = 'ios/App/App.xcodeproj'
abort "Xcode project not found at #{project_path} — run setup.sh first" unless File.exist?(project_path)

project = Xcodeproj::Project.open(project_path)
group   = project.main_group['App']
target  = project.targets.first

Dir['ios-plugins/*.swift'].each do |src|
  filename = File.basename(src)
  next if group.find_file_by_path(filename)
  ref = group.new_file(filename)
  target.source_build_phase.add_file_reference(ref)
  puts "  + #{filename}"
end

project.save
puts "Xcode project saved."
