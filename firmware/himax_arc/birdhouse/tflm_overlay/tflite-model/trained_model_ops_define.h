// Birdhouse overlay for the vendor TFLite Micro operator configuration.
//
// The vendor SDK ships "tflite-model/trained_model_ops_define.h", generated for
// its bundled camera model. That header disables kernel code paths the bundled
// model does not use, including INT8 FULLY_CONNECTED. The Birdhouse model needs
// that path (two Dense layers), so with the vendor header alone the kernel is
// compiled as a stub that returns kTfLiteError.
//
// This file is placed earlier on the include path than the vendor header. It
// includes the vendor header unchanged and then re-enables only the code paths
// listed in model_manifest.json. Nothing in the vendor tree is edited.
//
// Verified by tools/himax/verify_tflm_ops.py; do not edit by hand without
// re-running that check.
#ifndef BIRDHOUSE_TFLM_OPS_OVERLAY_H_
#define BIRDHOUSE_TFLM_OPS_OVERLAY_H_

#include_next "tflite-model/trained_model_ops_define.h"

// FULLY_CONNECTED, INT8 input and output (operators 12 and 13 of the model).
#undef EI_TFLITE_DISABLE_FULLY_CONNECTED_IN_I8
#define EI_TFLITE_DISABLE_FULLY_CONNECTED_IN_I8 0
#undef EI_TFLITE_DISABLE_FULLY_CONNECTED_OUT_I8
#define EI_TFLITE_DISABLE_FULLY_CONNECTED_OUT_I8 0

// Marker so the build audit can prove this overlay was on the include path.
#define BIRDHOUSE_TFLM_OPS_OVERLAY 1

#endif  // BIRDHOUSE_TFLM_OPS_OVERLAY_H_
