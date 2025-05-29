#!/usr/bin/liquidsoap

# Liquidsoap main configuration for sculpture system
# Creates personalized mixes for each sculpture

# Set log level
set("log.level", 3)

# Enable telnet server for control
set("server.telnet", true)
set("server.telnet.bind_addr", "0.0.0.0")
set("server.telnet.port", 1234)

# Audio settings
set("frame.audio.samplerate", 48000)
set("frame.audio.channels", 1)

# Input sources from sculptures
# These will be the live microphone feeds from each sculpture
a1 = input.http(id="sculpture1_input", "http://localhost:8000/s1-mic.ogg")
a2 = input.http(id="sculpture2_input", "http://localhost:8000/s2-mic.ogg")
a3 = input.http(id="sculpture3_input", "http://localhost:8000/s3-mic.ogg")

# Add fallback silence for when inputs are not available
silence = blank()

a1_safe = fallback(id="a1_fallback", [a1, silence])
a2_safe = fallback(id="a2_fallback", [a2, silence])
a3_safe = fallback(id="a3_fallback", [a3, silence])

# Apply basic audio processing
def process_audio(s)
  # Simple amplification and limiting
  s = amplify(0.8, s)
  s = compress(s)
  s
end

a1_processed = process_audio(a1_safe)
a2_processed = process_audio(a2_safe)
a3_processed = process_audio(a3_safe)

# Create personalized mixes
# Each sculpture hears the other two sculptures, not itself
to1 = add([a2_processed, a3_processed])
to2 = add([a1_processed, a3_processed])
to3 = add([a1_processed, a2_processed])

# Apply final processing to mixes
to1_final = process_audio(to1)
to2_final = process_audio(to2)
to3_final = process_audio(to3)

# Output to Icecast
output.icecast(
  %vorbis(quality=0.5),
  host="localhost",
  port=8000,
  password="hackme",
  mount="mix-for-1.ogg",
  name="Mix for Sculpture 1",
  description="Personalized audio mix",
  to1_final
)

output.icecast(
  %vorbis(quality=0.5),
  host="localhost",
  port=8000,
  password="hackme",
  mount="mix-for-2.ogg",
  name="Mix for Sculpture 2",
  description="Personalized audio mix",
  to2_final
)

output.icecast(
  %vorbis(quality=0.5),
  host="localhost",
  port=8000,
  password="hackme",
  mount="mix-for-3.ogg",
  name="Mix for Sculpture 3",
  description="Personalized audio mix",
  to3_final
)

# Log startup
log("Sculpture system Liquidsoap configuration loaded")
log("Creating personalized mixes:")
log("  - mix-for-1.ogg: sculptures 2+3 for sculpture 1")
log("  - mix-for-2.ogg: sculptures 1+3 for sculpture 2") 
log("  - mix-for-3.ogg: sculptures 1+2 for sculpture 3") 