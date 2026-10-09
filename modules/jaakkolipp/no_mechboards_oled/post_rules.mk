# Drop the Mechboards keyboard-level OLED code so the keymap fully owns both
# displays. keyboards/mechboards/common/post_rules.mk adds display_oled.c, which
# writes to the screen from layer_state_set_kb, housekeeping_task_kb and others
# regardless of oled_task_user. Module post_rules.mk files are included after
# keyboard ones (builddefs/build_keyboard.mk), so filtering SRC here works.
MECHBOARDS_OLED_SRC := keyboards/mechboards/common/display_oled.c

ifneq ($(filter $(MECHBOARDS_OLED_SRC),$(SRC)),)
    SRC := $(filter-out $(MECHBOARDS_OLED_SRC),$(SRC))
else
    $(warning no_mechboards_oled: $(MECHBOARDS_OLED_SRC) not in SRC; upstream may have moved it)
endif
