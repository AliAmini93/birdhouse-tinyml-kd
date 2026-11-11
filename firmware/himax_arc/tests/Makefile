# Host tests for the Birdhouse Himax firmware module.
#
# Everything here runs on the development PC. Nothing talks to the board.
#
#   make -C firmware/himax_arc/tests run-tflm            # inference test, firmware operator config
#   make -C firmware/himax_arc/tests run-tflm CONFIG=vendor   # negative control: must be blocked
#   make -C firmware/himax_arc/tests run-unit            # capture/runtime/diagnostics tests
#   make -C firmware/himax_arc/tests run-all
#
# The TFLite Micro sources are compiled from the vendor SDK tree in place (not
# copied, not modified) with the reference kernels. CONFIG selects the operator
# configuration header seen by those kernels:
#   overlay  firmware/himax_arc/birdhouse/tflm_overlay is first on the include path
#   vendor   the vendor header only

REPO   ?= $(abspath $(dir $(lastword $(MAKEFILE_LIST)))/../../..)
SDK    ?= $(REPO)/.local-tools/source/firmware-seeed-grove-vision-ai/Synopsys_PA8535_EM9D_DFSS_SDK_3.3
EI_MODEL ?= $(SDK)/app/scenario_app/edge_impulse_visionai/ei-model
EI_SDK := $(EI_MODEL)/edge-impulse-sdk
BUILD  ?= $(REPO)/.local-tools/port-himax/host-tests
CONFIG ?= overlay
SAN    ?= 0

ifeq ($(filter $(CONFIG),overlay vendor),)
$(error CONFIG must be 'overlay' or 'vendor')
endif

ifeq ($(SAN),1)
OBJ := $(BUILD)/$(CONFIG)-san
else
OBJ := $(BUILD)/$(CONFIG)
endif
BH  := $(REPO)/firmware/himax_arc/birdhouse
T   := $(REPO)/firmware/himax_arc/tests

CXX ?= g++
CC  ?= gcc
AR  ?= ar

ifeq ($(CONFIG),overlay)
CFG_INC := -I$(BH)/tflm_overlay
else
CFG_INC :=
endif

# Same language level as the firmware build so host tests reject newer C++.
STD_CXX := -std=c++11
INC     := $(CFG_INC) -I$(EI_MODEL) -I$(REPO)
DEFS    := -DTF_LITE_STATIC_MEMORY -DBIRDHOUSE_HOST_BUILD=1
OPT     := -O2 -g
ifeq ($(SAN),1)
SANFLAGS := -fsanitize=address,undefined -fno-omit-frame-pointer
else
SANFLAGS :=
endif

VENDOR_CXXFLAGS := $(STD_CXX) $(OPT) $(DEFS) $(INC) -w
VENDOR_CFLAGS   := -std=gnu99 $(OPT) $(DEFS) $(INC) -w
# Vendor headers are reached through -isystem so that strict warnings apply to
# Birdhouse code only.
OUR_INC         := $(CFG_INC) -isystem $(EI_MODEL) -I$(REPO)
OUR_CXXFLAGS    := $(STD_CXX) $(OPT) $(DEFS) $(OUR_INC) -Wall -Wextra -Werror $(SANFLAGS)

# --- vendor TFLite Micro (reference kernels on a non-ARC host) ---------------
TFLM_CC  := $(shell find $(EI_SDK)/tensorflow -name '*.cc' | sort)
TFLM_C   := $(shell find $(EI_SDK)/tensorflow -name '*.c' | sort)
PORT_CPP := $(sort $(wildcard $(EI_SDK)/porting/posix/*.cpp))
TFLM_OBJS := $(patsubst $(EI_SDK)/%,$(OBJ)/tflm/%.o,$(TFLM_CC) $(TFLM_C) $(PORT_CPP))
TFLM_LIB := $(OBJ)/libtflm.a

$(OBJ)/tflm/%.cc.o: $(EI_SDK)/%.cc
	@mkdir -p $(dir $@)
	@$(CXX) $(VENDOR_CXXFLAGS) -c $< -o $@
$(OBJ)/tflm/%.cpp.o: $(EI_SDK)/%.cpp
	@mkdir -p $(dir $@)
	@$(CXX) $(VENDOR_CXXFLAGS) -c $< -o $@
$(OBJ)/tflm/%.c.o: $(EI_SDK)/%.c
	@mkdir -p $(dir $@)
	@$(CC) $(VENDOR_CFLAGS) -c $< -o $@

$(TFLM_LIB): $(TFLM_OBJS)
	@rm -f $@
	@$(AR) rcs $@ $^
	@echo "built $@ ($(words $(TFLM_OBJS)) objects, CONFIG=$(CONFIG))"

# Macro state seen by the host kernels, for tools/himax/verify_tflm_ops.py --host.
$(OBJ)/tflm_config.macros: $(BH)/build/tflm_config_probe.cc $(wildcard $(BH)/tflm_overlay/tflite-model/*.h)
	@mkdir -p $(dir $@)
	$(CXX) -E -dM $(VENDOR_CXXFLAGS) $< -o $@

# --- Birdhouse sources --------------------------------------------------------
$(OBJ)/repo/%.o: $(REPO)/%.cc
	@mkdir -p $(dir $@)
	$(CXX) $(OUR_CXXFLAGS) -MMD -MP -c $< -o $@

MODEL_OBJS := $(OBJ)/repo/firmware/model/student_final_int8_model_data.o \
              $(OBJ)/repo/firmware/himax_arc/birdhouse/bh_model.o

TFLM_TEST := $(OBJ)/test_tflm_inference
$(TFLM_TEST): $(OBJ)/repo/firmware/himax_arc/tests/test_tflm_inference.o $(MODEL_OBJS) $(TFLM_LIB)
	$(CXX) $(SANFLAGS) -o $@ $^ -lm

.PHONY: tflm run-tflm config-macros
tflm: $(TFLM_TEST)
config-macros: $(OBJ)/tflm_config.macros

ifeq ($(CONFIG),overlay)
run-tflm: $(TFLM_TEST)
	$(TFLM_TEST)
else
run-tflm: $(TFLM_TEST)
	$(TFLM_TEST) expect-blocked
endif

# --- capture / adapter / runtime tests ----------------------------------------
R := $(OBJ)/repo/firmware
CORE_OBJS    := $(R)/himax_arc/birdhouse/bh_capture.o $(R)/himax_arc/birdhouse/bh_diag.o
FAKE_OBJS    := $(R)/himax_arc/tests/fake_aud_lib.o $(R)/himax_arc/tests/host_port.o
PORT_OBJS    := $(R)/himax_arc/birdhouse/bh_pdm_port.o
PIPE_OBJS    := $(R)/himax_arc/birdhouse/bh_runtime.o $(R)/preprocess/audio_preprocess.o \
                $(R)/preprocess/mel_filterbank.o

$(OBJ)/test_diag: $(R)/himax_arc/tests/test_diag.o $(R)/himax_arc/birdhouse/bh_diag.o
	$(CXX) $(SANFLAGS) -o $@ $^
$(OBJ)/test_capture: $(R)/himax_arc/tests/test_capture.o $(R)/himax_arc/birdhouse/bh_capture.o
	$(CXX) $(SANFLAGS) -o $@ $^
$(OBJ)/test_pdm_port: $(R)/himax_arc/tests/test_pdm_port.o $(CORE_OBJS) $(PORT_OBJS) $(FAKE_OBJS)
	$(CXX) $(SANFLAGS) -o $@ $^
$(OBJ)/test_runtime: $(R)/himax_arc/tests/test_runtime.o $(CORE_OBJS) $(PORT_OBJS) $(FAKE_OBJS) \
                     $(PIPE_OBJS) $(MODEL_OBJS) $(TFLM_LIB)
	$(CXX) $(SANFLAGS) -o $@ $^ -lm

UNIT_TESTS := $(OBJ)/test_diag $(OBJ)/test_capture $(OBJ)/test_pdm_port $(OBJ)/test_runtime

.PHONY: unit run-unit run-all
unit: $(UNIT_TESTS)
run-unit: $(UNIT_TESTS)
	@for t in $(UNIT_TESTS); do echo "=== $$t"; $$t || exit 1; done
run-all: run-tflm run-unit

-include $(shell find $(OBJ)/repo -name '*.d' 2>/dev/null)

.PHONY: clean
clean:
	rm -rf $(BUILD)
