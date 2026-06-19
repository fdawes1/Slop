#----------------------------------------------------------------
# Generated CMake target import file for configuration "Release".
#----------------------------------------------------------------

# Commands may need to know the format version.
set(CMAKE_IMPORT_FILE_VERSION 1)

# Import target "realsense2::rsutils" for configuration "Release"
set_property(TARGET realsense2::rsutils APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(realsense2::rsutils PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/librsutils.a"
  )

list(APPEND _cmake_import_check_targets realsense2::rsutils )
list(APPEND _cmake_import_check_files_for_realsense2::rsutils "${_IMPORT_PREFIX}/lib/librsutils.a" )

# Import target "realsense2::realsense-file" for configuration "Release"
set_property(TARGET realsense2::realsense-file APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(realsense2::realsense-file PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "C;CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/librealsense-file.a"
  )

list(APPEND _cmake_import_check_targets realsense2::realsense-file )
list(APPEND _cmake_import_check_files_for_realsense2::realsense-file "${_IMPORT_PREFIX}/lib/librealsense-file.a" )

# Import target "realsense2::rs_lz4" for configuration "Release"
set_property(TARGET realsense2::rs_lz4 APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(realsense2::rs_lz4 PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "C"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/librs_lz4.a"
  )

list(APPEND _cmake_import_check_targets realsense2::rs_lz4 )
list(APPEND _cmake_import_check_files_for_realsense2::rs_lz4 "${_IMPORT_PREFIX}/lib/librs_lz4.a" )

# Import target "realsense2::sqlite3_lib" for configuration "Release"
set_property(TARGET realsense2::sqlite3_lib APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(realsense2::sqlite3_lib PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "C"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libsqlite3_lib.a"
  )

list(APPEND _cmake_import_check_targets realsense2::sqlite3_lib )
list(APPEND _cmake_import_check_files_for_realsense2::sqlite3_lib "${_IMPORT_PREFIX}/lib/libsqlite3_lib.a" )

# Import target "realsense2::realdds" for configuration "Release"
set_property(TARGET realsense2::realdds APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(realsense2::realdds PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/librealdds.a"
  )

list(APPEND _cmake_import_check_targets realsense2::realdds )
list(APPEND _cmake_import_check_files_for_realsense2::realdds "${_IMPORT_PREFIX}/lib/librealdds.a" )

# Import target "realsense2::fastrtps" for configuration "Release"
set_property(TARGET realsense2::fastrtps APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(realsense2::fastrtps PROPERTIES
  IMPORTED_LINK_INTERFACE_LANGUAGES_RELEASE "CXX"
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/libfastrtps.a"
  )

list(APPEND _cmake_import_check_targets realsense2::fastrtps )
list(APPEND _cmake_import_check_files_for_realsense2::fastrtps "${_IMPORT_PREFIX}/lib/libfastrtps.a" )

# Import target "realsense2::realsense2" for configuration "Release"
set_property(TARGET realsense2::realsense2 APPEND PROPERTY IMPORTED_CONFIGURATIONS RELEASE)
set_target_properties(realsense2::realsense2 PROPERTIES
  IMPORTED_LOCATION_RELEASE "${_IMPORT_PREFIX}/lib/librealsense2.so.2.58.2"
  IMPORTED_SONAME_RELEASE "librealsense2.so.2.58"
  )

list(APPEND _cmake_import_check_targets realsense2::realsense2 )
list(APPEND _cmake_import_check_files_for_realsense2::realsense2 "${_IMPORT_PREFIX}/lib/librealsense2.so.2.58.2" )

# Commands beyond this point should not need to know the version.
set(CMAKE_IMPORT_FILE_VERSION)
