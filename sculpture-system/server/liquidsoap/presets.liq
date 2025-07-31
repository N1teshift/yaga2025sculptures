# Liquidsoap presets and helper functions for sculpture system

# Dynamic audio processing parameters (from audio_config.yml)
compress_ratio = ref({{ audio_processing.compress_ratio }})
compress_threshold = ref({{ audio_processing.compress_threshold }})
attack_time = ref({{ audio_processing.attack_time }})
release_time = ref({{ audio_processing.release_time }})
highpass_freq = ref({{ audio_processing.highpass_freq }})
lowpass_freq = ref({{ audio_processing.lowpass_freq }})
delay_time = ref({{ audio_processing.delay_time }})
delay_feedback = ref({{ audio_processing.delay_feedback }})
gate_threshold = ref({{ audio_processing.gate_threshold }})
normalize_target = ref({{ audio_processing.normalize_target }})

# Processing bypass flag
processing_bypass = ref(false)

# Audio processing presets (now dynamic)
let sculpture_normalize = fun(s) ->
  normalize.old(target=!normalize_target, window=1.0, s)

let sculpture_compress = fun(s) ->
  compress(
    attack=!attack_time,
    release=!release_time, 
    ratio=!compress_ratio,
    threshold=!compress_threshold,
    s
  )

let sculpture_highpass = fun(s) ->
  filter.iir.butterworth.high(
    frequency=!highpass_freq,
    order=2,
    s
  )

let sculpture_lowpass = fun(s) ->
  filter.iir.butterworth.low(
    frequency=!lowpass_freq,
    order=2,
    s
  )

let sculpture_delay = fun(s) ->
  if !delay_time > 0.0 then
    add(normalize=false, [
      s,
      amplify(!delay_feedback, delay(!delay_time, s))
    ])
  else
    s
  end

let sculpture_gate = fun(s) ->
  gate(threshold=!gate_threshold, s)

# Combined processing chain (now dynamic with bypass option)
def sculpture_process(s) =
  # Create processed version
  processed = sculpture_gate(
    sculpture_delay(
      sculpture_lowpass(
        sculpture_highpass(
          sculpture_compress(
            sculpture_normalize(s)
          )
        )
      )
    )
  )
  
  # Use switch to select between processed and unprocessed
  switch(
    [
      (fun() -> !processing_bypass, s),
      (fun() -> true, processed)
    ]
  )
end

# Stereo to mono conversion (used by main.liq input sources)
let to_mono = fun(s) ->
  mean(s)

