EXTRA_OBJS += $(BIRD_OBJROOT)/audio_preprocess.o
EXTRA_OBJS += $(BIRD_OBJROOT)/mel_filterbank.o
EXTRA_OBJS += $(BIRD_OBJROOT)/student_final_int8_model_data.o
EXTRA_OBJS += $(BIRD_OBJROOT)/bird_model_himax_compat.o
EXTRA_OBJS += $(BIRD_OBJROOT)/birdhouse_link_probe.o

LINK_OPT += -Wl,--undefined=birdhouse_link_probe
