# Birdhouse build overlay for the vendor Himax SDK.
#
# Read by make *after* the SDK makefile:
#   make -C <sdk> -f makefile -f <this file> APP_TYPE=edge_impulse_visionai \
#        OUT_DIR_ROOT=<out> BH_REPO=<repo> BH_OBJ=<out>/birdhouse ...
# Use tools/himax/sdk_make.sh rather than calling make by hand.
#
# Nothing in the vendor tree is edited. The overlay only
#   1. puts one directory in front of the vendor include path, and
#   2. adds Birdhouse objects and link options to the vendor link.

ifndef BH_REPO
$(error BH_REPO (repository root) is required)
endif
ifndef BH_OBJ
$(error BH_OBJ (object directory for Birdhouse files) is required)
endif

# 1 = build TFLite Micro kernels with the Birdhouse operator overlay (normal).
# 0 = vendor configuration only; used by the negative test that reproduces the
#     disabled INT8 FULLY_CONNECTED kernel.
BH_TFLM_OVERLAY ?= 1

# 1 = link the Birdhouse module into the firmware (normal).
# 0 = vendor firmware only.
BH_LINK ?= 1

BH_SRC_DIR := $(BH_REPO)/firmware/himax_arc/birdhouse

# 1 = also emit per-function stack usage files (*.su) next to every object the
# SDK compiles. Does not change generated code; read by tools/himax/postlink_audit.py.
BH_STACK_USAGE ?= 1
ifeq ($(BH_STACK_USAGE),1)
override ALL_DEFINES += -fstack-usage
endif

ifeq ($(BH_TFLM_OVERLAY),1)
# ALL_DEFINES precedes the SDK include list on every compile line, so this
# directory is searched first for "tflite-model/trained_model_ops_define.h".
# The SDK sets ALL_DEFINES with "override ... := $(sort ...)" and also sorts its
# include list alphabetically, so the directory must be appended here with
# "override"; adding it to the SDK include list would not put it first.
override ALL_DEFINES += -I$(BH_SRC_DIR)/tflm_overlay
endif

# ---------------------------------------------------------------------------
# Operator configuration probe: preprocess one file with the exact firmware
# flags and dump every macro. Consumed by tools/himax/verify_tflm_ops.py.
# ---------------------------------------------------------------------------
.PHONY: bh_tflm_config
bh_tflm_config: MKDEP_OPT :=
bh_tflm_config: $(CORE_ARG_FILES)
	@mkdir -p $(BH_OBJ)
	$(CXX) -E -dM $(TCF_FLAGS) $(ALL_DEFINES) $(CXX_COMPILE_OPT) \
	    $(BH_SRC_DIR)/build/tflm_config_probe.cc -o $(BH_OBJ)/tflm_config.macros
	@echo "Wrote $(BH_OBJ)/tflm_config.macros"

# ---------------------------------------------------------------------------
# Birdhouse module: compiled with the firmware flags, linked into the vendor
# application. The vendor entry point is untouched; two functions are
# interposed with --wrap (see bh_arc_glue.cc).
# ---------------------------------------------------------------------------
ifeq ($(BH_LINK),1)

BH_SOURCES := \
    firmware/himax_arc/birdhouse/bh_console.cc \
    firmware/himax_arc/birdhouse/bh_capture.cc \
    firmware/himax_arc/birdhouse/bh_diag.cc \
    firmware/himax_arc/birdhouse/bh_model.cc \
    firmware/himax_arc/birdhouse/bh_runtime.cc \
    firmware/himax_arc/birdhouse/bh_pdm_port.cc \
    firmware/himax_arc/birdhouse/bh_arc_glue.cc \
    firmware/preprocess/audio_preprocess.cc \
    firmware/preprocess/mel_filterbank.cc \
    firmware/model/student_final_int8_model_data.cc

BH_OBJS := $(patsubst %.cc,$(BH_OBJ)/%.o,$(BH_SOURCES))
BH_VENDOR_APP := app/scenario_app/edge_impulse_visionai
BH_VENDOR_SYSTEM := -isystem $(BH_VENDOR_APP) -isystem $(BH_VENDOR_APP)/ei-model

$(BH_OBJS): $(BH_OBJ)/%.o: $(BH_REPO)/%.cc $(CORE_ARG_FILES) $(BH_SRC_DIR)/build/birdhouse_overlay.mk
	@mkdir -p $(dir $@)
	@echo "Compiling (birdhouse)  :  $*.cc"
	$(Q)$(CXX) -c $(TCF_FLAGS) $(ALL_DEFINES) $(CXX_COMPILE_OPT) $(BH_VENDOR_SYSTEM) -I$(BH_REPO) -Wall -Wextra -Werror -Wno-error=cpp $< -o $@

EXTRA_OBJS += $(BH_OBJS)
LINK_OPT += -Wl,--wrap=is_inference_running
LINK_OPT += -Wl,--wrap=hx_drv_pdm_deinit
LINK_OPT += -Wl,--wrap=_dma_chan_enable
LINK_OPT += -Wl,--wrap=_ZN8ATParser5parseENSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE

$(APPL_FULL_NAME).elf: $(BH_OBJS)

-include $(BH_OBJS:.o=.o.d)

endif
