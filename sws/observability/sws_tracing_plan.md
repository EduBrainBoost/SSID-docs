# SWS Tracing Plan

Scope: SWS V1.0 → V1.5. Establishes consistent trace/span structure for
analyze and rebuild pipelines.

## Span hierarchy

```
span: sws.job                  [attributes: job_id, mode, rights_class]
  span: sws.attempt            [attributes: attempt_id, attempt_number]
    span: sws.stage.rights_check
    span: sws.stage.ingest
    span: sws.stage.video_analysis
    span: sws.stage.audio_analysis
    span: sws.stage.transcript
    span: sws.stage.ocr
    span: sws.stage.narrative_hook
    span: sws.stage.blueprint_compile
    (rebuild mode):
    span: sws.stage.replacement_plan
    span: sws.stage.timeline_build
    span: sws.stage.render
```

## Attribute contract

Required attributes on every stage span:
- `sws.stage`           (string)  e.g. "ingest"
- `sws.job_id`          (string)
- `sws.attempt_id`      (string)
- `sws.mode`            (string)  analyze_url | analyze_file | rebuild
- `sws.stage.status`    (string)  running | succeeded | failed | skipped
- `sws.stage.error_code`(string, optional)

Optional stage-specific:
- ingest: `sws.source.sha256`, `sws.source.byte_size`
- video_analysis: `sws.shots.count`
- transcript: `sws.transcript.segments`, `sws.transcript.language`
- render: `sws.render.status`, `sws.render.output_sha256`

## Exporter

V1.5 target: OpenTelemetry OTLP over HTTP/gRPC to an OTEL collector. For V1.0,
span data is serialised to `job_events.jsonl` per attempt (`event_type ==
"stage_finished"`) which is sufficient for post-mortem analysis.

## Correlation IDs

- `job_id` is the primary correlation ID across all logs/artifacts.
- `attempt_id` distinguishes retries; old attempts are never mutated.
- Trace IDs (when OTEL is wired) map 1:1 to an `sws.job` span.

## Sampling

- V1.0 / V1.5: sample all jobs (low volume expected).
- V2.0+: 100% sample on failed and R3/R4 jobs; 10% on R0/R1 successes.
