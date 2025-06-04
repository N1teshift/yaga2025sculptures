#!/usr/bin/liquidsoap

# Liquidsoap main configuration for sculpture system
# Supports dynamic plan switching via telnet

# Import presets
%include "presets.liq"

# Set log level
set("log.level", 4)

# Enable telnet server for control
set("server.telnet", true)
set("server.telnet.bind_addr", "0.0.0.0")
set("server.telnet.port", 1234)

# Audio settings
set("frame.audio.samplerate", 48000)
set("frame.audio.channels", 1)

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

s1_safe = fallback(id="s1_fallback", [s1_mono, silence])
s2_safe = fallback(id="s2_fallback", [s2_mono, silence])
s3_safe = fallback(id="s3_fallback", [s3_mono, silence])

# Process audio using presets if available
s1_proc = sculpture_process(s1_safe)
s2_proc = sculpture_process(s2_safe)
s3_proc = sculpture_process(s3_safe)

# Prerecorded file for local mode (replace with actual file path when available)
prerecorded = sine(440.0)

# Reference to current plan (default: B1)
current_plan = ref "B1"

# Mix output references updated when the plan changes
to1 = ref(silence)
to2 = ref(silence)
to3 = ref(silence)

# Function to create mixes based on plan
# Returns: (to1, to2, to3)
def get_mixes(plan)
  log("info", "Getting plan: #{x['title']} mix")
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

# Telnet command to set plan
def set_plan(arg)
  if arg == "" then
    "Usage: set_plan <A1|A2|B1|B2|B3|C|D>"
  else
    current_plan := arg
    update_mixes()
    log("Plan changed to #{arg}")
    "Plan set to #{arg}"
  end
end
server.register("set_plan", set_plan)

# Update mix references based on the current plan
def update_mixes()
  log("info", "Mixes getting updated")
  mixes = get_mixes(!current_plan)
  to1 := list.hd(mixes)
  to2 := list.hd(list.tl(mixes))
  to3 := list.hd(list.tl(list.tl(mixes)))
end

# Initialize mixes
update_mixes()

def get_plan(_) = !current_plan  # ignore arg, return value
server.register("get_plan", get_plan)

# Apply final processing to mixes
to1_final = to_mono(sculpture_process(!to1))
to2_final = to_mono(sculpture_process(!to2))
to3_final = to_mono(sculpture_process(!to3))

# Output to Icecast
output.icecast(
  %vorbis(quality=0.5, channels=1),
  host="localhost",
  port=8000,
  password="hackme",
  mount="mix-for-1.ogg",
  name="Mix for Sculpture 1",
  description="Personalized audio mix",
  to1_final
)

output.icecast(
  %vorbis(quality=0.5, channels=1),
  host="localhost",
  port=8000,
  password="hackme",
  mount="mix-for-2.ogg",
  name="Mix for Sculpture 2",
  description="Personalized audio mix",
  to2_final
)

output.icecast(
  %vorbis(quality=0.5, channels=1),
  host="localhost",
  port=8000,
  password="hackme",
  mount="mix-for-3.ogg",
  name="Mix for Sculpture 3",
  description="Personalized audio mix",
  to3_final
)

# Log startup
log("Sculpture system Liquidsoap configuration loaded (dynamic plans)")
