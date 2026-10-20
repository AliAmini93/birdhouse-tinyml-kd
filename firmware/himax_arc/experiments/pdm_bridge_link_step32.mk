EXTRA_OBJS += $(BIRD_PORT)/pdm_stream_bridge_arc.o
LINK_OPT += -Wl,--undefined=birdhouse_pdm_feed
