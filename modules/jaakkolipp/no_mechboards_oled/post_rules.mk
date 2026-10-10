# Drop the Mechboards keyboard-level OLED code so the keymap fully owns both
# displays. keyboards/mechboards/common/post_rules.mk adds display_oled.c, which
# writes to the screen from layer_state_set_kb, housekeeping_task_kb and others
# regardless of oled_task_user. Module post_rules.mk files are included after
# keyboard ones (builddefs/build_keyboard.mk), so editing SRC here works.
#
# SRC is a recursively expanded variable that still holds references such as
# $(BOOTLOADER) which are only set later, so the edit is done on its
# unexpanded value instead of with ":=" (which would expand them too early).
MECHBOARDS_OLED_SRC := keyboards/mechboards/common/display_oled.c

ifneq ($(findstring $(MECHBOARDS_OLED_SRC),$(value SRC)),)
    ifeq ($(flavor SRC),recursive)
        NO_MECHBOARDS_OLED_SRC := $(subst $(MECHBOARDS_OLED_SRC),,$(value SRC))
        $(eval SRC = $(NO_MECHBOARDS_OLED_SRC))
    else
        SRC := $(filter-out $(MECHBOARDS_OLED_SRC),$(SRC))
    endif
else
    $(warning no_mechboards_oled: $(MECHBOARDS_OLED_SRC) not in SRC; upstream may have moved it)
endif
