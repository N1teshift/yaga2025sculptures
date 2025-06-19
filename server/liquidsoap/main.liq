#!/usr/bin/liquidsoap

# Liquidsoap main configuration for sculpture system
# Supports dynamic plan switching via telnet

# Import presets
%include "presets.liq"

# Set log level
settings.log.level.set(4)

# Enable telnet server for control
settings.server.telnet.set(true)
settings.server.telnet.bind_addr.set("0.0.0.0")
settings.server.telnet.port.set(1234)

# Audio settings
settings.frame.audio.samplerate.set(44100)
# settings.frame.audio.channels.set(1) # Let liquidsoap handle channels dynamically

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

# Reference to current plan (default: B1)
current_plan = ref("B1")

# Mix output references updated when the plan changes
to1 = ref(silence)
to2 = ref(silence)
to3 = ref(silence)


# Function to create mixes based on plan
# Returns: [to1, to2, to3]
def get_mixes(plan)
  if plan == "A1" then
    # 1 hears 2, 2 hears 3, 3 hears 1
    [s2_proc, s3_proc, s1_proc]
  elsif plan == "A2" then
    # 1 hears 3, 2 hears 1, 3 hears 2
    [s3_proc, s1_proc, s2_proc]
  elsif plan == "B1" then
    # 1<->2, 3 silent
    [s2_proc, s1_proc, silence]
  elsif plan == "B2" then
    # 2<->3, 1 silent
    [silence, s3_proc, s2_proc]
  elsif plan == "B3" then
    # 3<->1, 2 silent
    [s3_proc, silence, s1_proc]
  elsif plan == "C" then
    # All-to-all except self
    [add([s2_proc, s3_proc]), add([s1_proc, s3_proc]), add([s1_proc, s2_proc])]
  elsif plan == "D" then
    # All outputs play prerecorded file
    [prerecorded, prerecorded, prerecorded]
  else
    # Fallback to A1
    [s2_proc, s3_proc, s1_proc]
  end
end

# Update mix references based on the current plan
def update_mixes()
  mixes = get_mixes(!current_plan)
  to1 := list.hd(mixes)
  to2 := list.hd(list.tl(mixes))
  to3 := list.hd(list.tl(list.tl(mixes)))
end

# Telnet command to set plan
def set_plan(arg)
  # Allowed plans
  plans = ["A1", "A2", "B1", "B2", "B3", "C", "D"]
  
  if list.mem(arg, plans) then
    log("Setting plan to #{arg}...")
    # Update the reference
    current_plan := arg
    # Reload the mixes with the new plan
    update_mixes()
    log("Plan changed to #{arg}")
    "Plan set to #{arg}"
  else
    "Unknown plan: #{arg}"
  end
end
server.register("set_plan", set_plan)

# Telnet command to get the current plan
def get_plan(_)
  !current_plan
end
server.register("get_plan", get_plan, description="Get the current plan.")

# Initialize mixes
update_mixes()

# The !toX refs now hold the final, processed audio.
# The `sculpture_process` function is already applied to the safe sources,
# so we can use the refs directly in the output.

# Output to Icecast
output.icecast(
  %vorbis(quality=0.5, channels=1),
  host="localhost",
  port=8000,
  password="hackme",
  mount="mix-for-1.ogg",
  name="Mix for Sculpture 1",
  description="Personalized audio mix",
  !to1
)

output.icecast(
  %vorbis(quality=0.5, channels=1),
  host="localhost",
  port=8000,
  password="hackme",
  mount="mix-for-2.ogg",
  name="Mix for Sculpture 2",
  description="Personalized audio mix",
  !to2
)

output.icecast(
  %vorbis(quality=0.5, channels=1),
  host="localhost",
  port=8000,
  password="hackme",
  mount="mix-for-3.ogg",
  name="Mix for Sculpture 3",
  description="Personalized audio mix",
  !to3
)

# Log startup
log("Sculpture system Liquidsoap configuration loaded (dynamic plans)")
