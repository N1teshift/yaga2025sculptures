#!/usr/bin/liquidsoap
settings.init.allow_root.set(true)

# Liquidsoap main configuration for sculpture system
# Supports dynamic plan switching via HTTP API

# Import presets
%include "presets.liq"

# Set log level
settings.log.level.set(4)
settings.log.file.path.set("/var/log/liquidsoap/main.log")

# Enable telnet server for server-agent communication.
# Bind to localhost only — the telnet API has no auth of its own.
settings.server.telnet.set(true)
settings.server.telnet.bind_addr.set("127.0.0.1")
settings.server.telnet.port.set(1234)

# Audio settings
settings.frame.audio.samplerate.set({{ audio_sample_rate }})
settings.frame.audio.channels.set({{ audio_channels }})

# Disable video to prevent it from overriding the audio samplerate
settings.frame.video.width.set(0)
settings.frame.video.height.set(0)

# Input sources from sculptures
# These will be the live microphone feeds from each sculpture
s1_input = input.http(id="sculpture1_input", "http://localhost:8000/s1-mic.ogg")
s2_input = input.http(id="sculpture2_input", "http://localhost:8000/s2-mic.ogg")
s3_input = input.http(id="sculpture3_input", "http://localhost:8000/s3-mic.ogg")

#To mono
s1_mono = to_mono(s1_input)
s2_mono = to_mono(s2_input)
s3_mono = to_mono(s3_input)

# Add fallback silence for when inputs are not available
silence = blank()

s1_safe = fallback(id="s1_fallback", track_sensitive=false, [s1_mono, silence])
s2_safe = fallback(id="s2_fallback", track_sensitive=false, [s2_mono, silence])
s3_safe = fallback(id="s3_fallback", track_sensitive=false, [s3_mono, silence])

# Process audio using presets if available
s1_proc = sculpture_process(s1_safe)
s2_proc = sculpture_process(s2_safe)
s3_proc = sculpture_process(s3_safe)

# Local-mode source for plan D. Point this at a real file when available;
# until then it falls back to silence so plan D is honest (no fake 440Hz tone).
prerecorded_file = getenv("LOCAL_MODE_FILE")
prerecorded =
  if prerecorded_file != "" then
    mksafe(single(prerecorded_file))
  else
    log("LOCAL_MODE_FILE not set; plan D will output silence")
    blank()
  end

# Build a list of processed sources indexed by sculpture number (1-based).
proc_sources = [s1_proc, s2_proc, s3_proc]

# Routing table: for each (recipient bus, plan) which source(s) feed its mix.
# Recipient bus: 1=A, 2=B, 3=C. Source ids: 1=s1, 2=s2, 3=s3, 0=silence, -1=prerecorded (plan D).
# ponytail: A1/A2 and B1..B3 collapsed to one bus per group; expand if per-sculpture routing is needed.
def mix_sources(recipient, plan)
  r = recipient
  p = plan
  if r == 1 and p == "A1" then [2]
  elsif r == 1 and p == "A2" then [3]
  elsif r == 1 and p == "B1" then [1]
  elsif r == 2 and p == "A1" then [3]
  elsif r == 2 and p == "A2" then [1]
  elsif r == 2 and p == "B1" then [2]
  elsif r == 3 and p == "A1" then [2, 3]
  elsif r == 3 and p == "A2" then [1, 3]
  elsif r == 3 and p == "B1" then [1, 2]
  elsif r == 1 and p == "D" then [-1]
  elsif r == 2 and p == "D" then [-1]
  elsif r == 3 and p == "D" then [-1]
  else [2]
  end
end

def source_for(id)
  if id == 0 then silence
  elsif id == -1 then prerecorded
  else list.nth(proc_sources, id - 1)
  end
end

# Reference to current plan (default: A1)
current_plan = ref("A1")

# Create dynamic sources that update when plan changes
to1_dynamic = source.dynamic()
to2_dynamic = source.dynamic()  
to3_dynamic = source.dynamic()

# Make dynamic sources infallible with fallback to silence
to1 = fallback(id="to1_fallback", track_sensitive=false, [to1_dynamic, silence])
to2 = fallback(id="to2_fallback", track_sensitive=false, [to2_dynamic, silence])
to3 = fallback(id="to3_fallback", track_sensitive=false, [to3_dynamic, silence])

# Resolve the mix source(s) for a recipient bus + plan into a single source.
def mix_source(recipient, plan)
  ids = mix_sources(recipient, plan)
  if list.length(ids) > 1 then
    add([source_for(list.nth(ids, 0)), source_for(list.nth(ids, 1))])
  else
    source_for(list.nth(ids, 0))
  end
end

# Function to update all mix sources based on current plan
def update_mixes()
  plan = !current_plan
  log("Updating mixes for plan: #{plan}")

  to1_dynamic.set(mix_source(1, plan))
  to2_dynamic.set(mix_source(2, plan))
  to3_dynamic.set(mix_source(3, plan))

  log("Mix updates completed for plan #{plan}")
end

# Plan switching functions
def set_plan_command(plan)
  log("Received set_plan command: #{plan}")
  
  # Allowed plans
  plans = ["A1", "A2", "B1", "B2", "B3", "C", "D"]
  
  if list.mem(plan, plans) then
    log("Setting plan...")
    # Update the reference
    current_plan := plan
    # Update all mixes with the new plan
    update_mixes()
    log("Plan changed")
    "Plan set"
  else
    log("Invalid plan requested")
    "Invalid plan. Valid plans: A1, A2, B1, B2, B3, C, D"
  end
end

def get_plan_command()
  log("Received get_plan command")
  !current_plan
end

# Register telnet commands for server-agent compatibility
server.register(
  "set_plan",
  fun(plan) -> set_plan_command(plan)
)

server.register(
  "get_plan", 
  fun(_) -> get_plan_command()
)

# Audio processing parameter commands
server.register(
  "set_compress_ratio",
  fun(val) -> begin
    compress_ratio := float_of_string(val);
    log("Compression ratio set");
    "Compression ratio set"
  end
)

server.register(
  "set_compress_threshold",
  fun(val) -> begin
    compress_threshold := float_of_string(val);
    log("Compression threshold set");
    "Compression threshold set"
  end
)

server.register(
  "set_attack_time",
  fun(val) -> begin
    attack_time := float_of_string(val);
    log("Attack time set");
    "Attack time set"
  end
)

server.register(
  "set_release_time",
  fun(val) -> begin
    release_time := float_of_string(val);
    log("Release time set");
    "Release time set"
  end
)

server.register(
  "set_highpass_freq",
  fun(val) -> begin
    highpass_freq := float_of_string(val);
    log("High-pass frequency set");
    "High-pass frequency set"
  end
)

server.register(
  "set_lowpass_freq",
  fun(val) -> begin
    lowpass_freq := float_of_string(val);
    log("Low-pass frequency set");
    "Low-pass frequency set"
  end
)

server.register(
  "set_delay_time",
  fun(val) -> begin
    delay_time := float_of_string(val);
    log("Delay time set");
    "Delay time set"
  end
)

server.register(
  "set_delay_feedback",
  fun(val) -> begin
    delay_feedback := float_of_string(val);
    log("Delay feedback set");
    "Delay feedback set"
  end
)

server.register(
  "set_gate_threshold",
  fun(val) -> begin
    gate_threshold := float_of_string(val);
    log("Gate threshold set");
    "Gate threshold set"
  end
)

server.register(
  "set_normalize_target",
  fun(val) -> begin
    normalize_target := float_of_string(val);
    log("Normalize target set");
    "Normalize target set"
  end
)

server.register(
  "reset_audio",
  fun(_) -> begin
    compress_ratio := {{ audio_processing.compress_ratio }};
    compress_threshold := {{ audio_processing.compress_threshold }};
    attack_time := {{ audio_processing.attack_time }};
    release_time := {{ audio_processing.release_time }};
    highpass_freq := {{ audio_processing.highpass_freq }};
    lowpass_freq := {{ audio_processing.lowpass_freq }};
    delay_time := {{ audio_processing.delay_time }};
    delay_feedback := {{ audio_processing.delay_feedback }};
    gate_threshold := {{ audio_processing.gate_threshold }};
    normalize_target := {{ audio_processing.normalize_target }};
    log("Audio processing reset to defaults");
    "Audio processing reset to defaults"
  end
)

server.register(
  "enable_processing",
  fun(_) -> begin
    processing_bypass := false;
    log("Audio processing enabled");
    "Audio processing enabled"
  end
)

server.register(
  "disable_processing", 
  fun(_) -> begin
    processing_bypass := true;
    log("Audio processing disabled (bypassed)");
    "Audio processing disabled (bypassed)"
  end
)

server.register(
  "get_processing_status",
  fun(_) -> begin
    if !processing_bypass then
      "disabled"
    else
      "enabled"
    end
  end
)

# Initialize mixes
update_mixes()

# The toX sources now dynamically switch based on current plan
# No dereferencing needed since they are direct sources

# Output to Icecast
output.icecast(
  %vorbis(quality={{ darkice_quality }}, channels={{ audio_channels }}),
  host="localhost",
  port=8000,
  password="{{ icecast_source_password | default("hackme") }}",
  mount="mix-for-1.ogg",
  name="Mix for Sculpture 1",
  description="Personalized audio mix",
  to1
)

output.icecast(
  %vorbis(quality={{ darkice_quality }}, channels={{ audio_channels }}),
  host="localhost",
  port=8000,
  password="{{ icecast_source_password | default("hackme") }}",
  mount="mix-for-2.ogg",
  name="Mix for Sculpture 2", 
  description="Personalized audio mix",
  to2
)

output.icecast(
  %vorbis(quality={{ darkice_quality }}, channels={{ audio_channels }}),
  host="localhost",
  port=8000,
  password="{{ icecast_source_password | default("hackme") }}",
  mount="mix-for-3.ogg",
  name="Mix for Sculpture 3",
  description="Personalized audio mix",
  to3
)

# Log startup
log("Sculpture system Liquidsoap configuration loaded with telnet API (port 1234)")
log("Available telnet commands:")
log("  set_plan <PLAN> - Set plan (A1, A2, B1, B2, B3, C, D)")
log("  get_plan        - Get current plan")
log("Audio processing commands:")
log("  set_compress_ratio <VALUE>     - Set compression ratio (1.0-10.0)")
log("  set_compress_threshold <VALUE> - Set compression threshold (-30.0-0.0)")
log("  set_attack_time <VALUE>        - Set attack time (0.01-1.0)")
log("  set_release_time <VALUE>       - Set release time (0.1-5.0)")
log("  set_highpass_freq <VALUE>      - Set high-pass frequency (20-500)")
log("  set_lowpass_freq <VALUE>       - Set low-pass frequency (1000-20000)")
log("  set_delay_time <VALUE>         - Set delay time (0.0-2.0)")
log("  set_delay_feedback <VALUE>     - Set delay feedback (0.0-0.9)")
log("  set_gate_threshold <VALUE>     - Set gate threshold (-60.0--10.0)")
log("  set_normalize_target <VALUE>   - Set normalize target (-24.0--6.0)")
log("  reset_audio                    - Reset all audio processing to defaults")
log("  enable_processing              - Enable audio processing")
log("  disable_processing             - Disable audio processing")
log("  get_processing_status          - Get audio processing status")

