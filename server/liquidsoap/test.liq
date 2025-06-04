s1 = input.http("http://localhost:8000/s1-mic.ogg")
s1_mono = add([s1])
safe_s1 = fallback([s1_mono, blank()])

output.icecast(
  %vorbis(quality=0.5, channels=1, samplerate=48000),
  host="localhost",
  port=8000,
  password="hackme",
  mount="test-s1.ogg",
  name="Test S1",
  safe_s1
)