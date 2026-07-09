# Distributed under the OSI-approved BSD 3-Clause License.  See accompanying
# file Copyright.txt or https://cmake.org/licensing for details.

cmake_minimum_required(VERSION 3.5)

file(MAKE_DIRECTORY
  "/home/armin/esp/esp-idf/components/bootloader/subproject"
  "/media/armin/External/AhmadWorks/audioclassification/firmware/esp32s3_preprocess_inference/build/bootloader"
  "/media/armin/External/AhmadWorks/audioclassification/firmware/esp32s3_preprocess_inference/build/bootloader-prefix"
  "/media/armin/External/AhmadWorks/audioclassification/firmware/esp32s3_preprocess_inference/build/bootloader-prefix/tmp"
  "/media/armin/External/AhmadWorks/audioclassification/firmware/esp32s3_preprocess_inference/build/bootloader-prefix/src/bootloader-stamp"
  "/media/armin/External/AhmadWorks/audioclassification/firmware/esp32s3_preprocess_inference/build/bootloader-prefix/src"
  "/media/armin/External/AhmadWorks/audioclassification/firmware/esp32s3_preprocess_inference/build/bootloader-prefix/src/bootloader-stamp"
)

set(configSubDirs )
foreach(subDir IN LISTS configSubDirs)
    file(MAKE_DIRECTORY "/media/armin/External/AhmadWorks/audioclassification/firmware/esp32s3_preprocess_inference/build/bootloader-prefix/src/bootloader-stamp/${subDir}")
endforeach()
if(cfgdir)
  file(MAKE_DIRECTORY "/media/armin/External/AhmadWorks/audioclassification/firmware/esp32s3_preprocess_inference/build/bootloader-prefix/src/bootloader-stamp${cfgdir}") # cfgdir has leading slash
endif()
