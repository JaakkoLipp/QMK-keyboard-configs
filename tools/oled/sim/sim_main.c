// Renders one OLED frame for a scenario given as key=value arguments and
// prints the 512-byte frame buffer as hex. Driven by tools/oled/preview.py.
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "qmk_stub.h"
#include "fi_keys.h"
#include "shared.h"

layer_state_t layer_state;
user_config_t user_config;
shared_t      g_shared;

static uint8_t  buffer[512];
static uint8_t  mods, oneshot, wpm, left = 1;
static led_t    leds;
static uint32_t now_ms;
static bool     windows = true;

uint8_t get_highest_layer(layer_state_t s) {
    for (int i = 31; i >= 0; i--)
        if (s & (1UL << i)) return i;
    return 0;
}
uint8_t  get_mods(void) { return mods; }
uint8_t  get_oneshot_mods(void) { return oneshot; }
led_t    host_keyboard_led_state(void) { return leds; }
uint8_t  get_current_wpm(void) { return wpm; }
uint32_t timer_read32(void) { return now_ms; }
uint32_t last_input_activity_elapsed(void) { return 0; }
bool     is_keyboard_left(void) { return left; }
bool     is_oled_on(void) { return true; }
bool     oled_off(void) { return true; }
void     oled_clear(void) {}
void     oled_write_raw_byte(const char data, uint16_t index) { if (index < sizeof(buffer)) buffer[index] = data; }
void     eeconfig_update_user(uint32_t v) {}
uint32_t eeconfig_read_user(void) { return 0; }
bool     os_is_windows(void) { return windows; }
bool     shared_layer_locked(uint8_t layer) { return g_shared.locked_layers & (1 << layer); }
bool     shared_caps_word(void) { return g_shared.flags & SHF_CAPS_WORD; }
void     user_config_save(void) {}

bool oled_task_user(void);

int main(int argc, char **argv) {
    layer_state         = 1;
    g_shared.claude_ctx = 0xFF;
    for (int i = 1; i < argc; i++) {
        char *eq = strchr(argv[i], '=');
        if (!eq) continue;
        *eq             = 0;
        const char *k   = argv[i];
        const char *v   = eq + 1;
        const long  n   = strtol(v, NULL, 0);
        if (!strcmp(k, "side")) left = !strcmp(v, "left");
        else if (!strcmp(k, "layers")) layer_state = n;
        else if (!strcmp(k, "mods")) mods = n;
        else if (!strcmp(k, "oneshot")) oneshot = n;
        else if (!strcmp(k, "wpm")) wpm = n;
        else if (!strcmp(k, "time")) now_ms = n;
        else if (!strcmp(k, "caps")) leds.caps_lock = n;
        else if (!strcmp(k, "numlock")) leds.num_lock = n;
        else if (!strcmp(k, "linux")) windows = !n;
        else if (!strcmp(k, "os_mode")) user_config.os_mode = n;
        else if (!strcmp(k, "locked")) g_shared.locked_layers = n;
        else if (!strcmp(k, "caps_word")) g_shared.flags |= n ? SHF_CAPS_WORD : 0;
        else if (!strcmp(k, "clock")) { const long c = strtol(v, NULL, 10); g_shared.flags |= SHF_CLOCK_VALID; g_shared.hour = c / 100; g_shared.minute = c % 100; }
        else if (!strcmp(k, "keys")) g_shared.keystrokes = n;
        else if (!strcmp(k, "claude")) g_shared.claude_state = n;
        else if (!strcmp(k, "tool")) strncpy(g_shared.claude_tool, v, CLAUDE_TOOL_LEN);
        else if (!strcmp(k, "turn")) g_shared.claude_turn_s = n;
        else if (!strcmp(k, "ctx")) g_shared.claude_ctx = n;
        else if (!strcmp(k, "others")) g_shared.claude_others = n;
    }
    oled_task_user();
    for (size_t i = 0; i < sizeof(buffer); i++) printf("%02x", buffer[i]);
    printf("\n");
    return 0;
}
