#!/usr/bin/liquidsoap

# Liquidsoap main configuration for sculpture system
# Supports dynamic plan switching via HTTP API

# Import presets
%include "presets.liq"

# Set log level
settings.log.level.set(4)
settings.log.file.path.set("/var/log/liquidsoap/main.log")

# Enable telnet server for server-agent communication
settings.server.telnet.set(true)
settings.server.telnet.bind_addr.set("0.0.0.0")
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

# Prerecorded file for local mode (replace with actual file path when available)
prerecorded = sine(440.0)

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

# Function to update all mix sources based on current plan
def update_mixes()
  plan = !current_plan
  log("Updating mixes for plan: #{plan}")
  
  # Update sculpture 1 mix
  if plan == "A1" then to1_dynamic.set(s2_proc)
  elsif plan == "A2" then to1_dynamic.set(s3_proc)  
  elsif plan == "B1" then to1_dynamic.set(s2_proc)
  elsif plan == "B2" then to1_dynamic.set(silence)
  elsif plan == "B3" then to1_dynamic.set(s3_proc)
  elsif plan == "C" then to1_dynamic.set(add([s2_proc, s3_proc]))
  elsif plan == "D" then to1_dynamic.set(prerecorded)
  else to1_dynamic.set(s2_proc) end
  
  # Update sculpture 2 mix
  if plan == "A1" then to2_dynamic.set(s3_proc)
  elsif plan == "A2" then to2_dynamic.set(s1_proc)
  elsif plan == "B1" then to2_dynamic.set(s1_proc)  
  elsif plan == "B2" then to2_dynamic.set(s3_proc)
  elsif plan == "B3" then to2_dynamic.set(silence)
  elsif plan == "C" then to2_dynamic.set(add([s1_proc, s3_proc]))
  elsif plan == "D" then to2_dynamic.set(prerecorded)
  else to2_dynamic.set(s3_proc) end
  
  # Update sculpture 3 mix
  if plan == "A1" then to3_dynamic.set(s1_proc)
  elsif plan == "A2" then to3_dynamic.set(s2_proc)
  elsif plan == "B1" then to3_dynamic.set(silence)
  elsif plan == "B2" then to3_dynamic.set(s2_proc)  
  elsif plan == "B3" then to3_dynamic.set(s1_proc)
  elsif plan == "C" then to3_dynamic.set(add([s1_proc, s2_proc]))
  elsif plan == "D" then to3_dynamic.set(prerecorded)
  else to3_dynamic.set(s1_proc) end
  
  log("Mix updates completed for plan #{plan}")
end

# Plan switching functions
def set_plan_command(plan)
  log("Received set_plan command: #{plan}")
  
  # Allowed plans
  plans = ["A1", "A2", "B1", "B2", "B3", "C", "D"]
  
  if list.mem(plan, plans) then
    log("Setting plan to #{plan}...")
    # Update the reference
    current_plan := plan
    # Update all mixes with the new plan
    update_mixes()
    log("Plan changed to #{plan}")
    "Plan set to #{plan}"
  else
    log("Invalid plan requested: #{plan}")
    "Invalid plan #{plan}. Valid plans: A1, A2, B1, B2, B3, C, D"
  end
end

def get_plan_command()
  log("Received get_plan command")
  "#{!current_plan}"
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

# Initialize mixes
update_mixes()

# The toX sources now dynamically switch based on current plan
# No dereferencing needed since they are direct sources

# Output to Icecast
output.icecast(
  %vorbis(quality={{ darkice_quality }}, channels={{ audio_channels }}),
  host="localhost",
  port=8000,
  password="hackme",
  mount="mix-for-1.ogg",
  name="Mix for Sculpture 1",
  description="Personalized audio mix",
  to1
)

output.icecast(
  %vorbis(quality={{ darkice_quality }}, channels={{ audio_channels }}),
  host="localhost",
  port=8000,
  password="hackme",
  mount="mix-for-2.ogg",
  name="Mix for Sculpture 2", 
  description="Personalized audio mix",
  to2
)

output.icecast(
  %vorbis(quality={{ darkice_quality }}, channels={{ audio_channels }}),
  host="localhost",
  port=8000,
  password="hackme",
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

