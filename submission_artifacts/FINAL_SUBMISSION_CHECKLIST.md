# ROCmRoute Zero Final Submission Checklist

## Image build

Build from commit `17513e3` or later on branch `codex/amd-notebook-test`:

```bash
docker build -f Dockerfile.leaderboard -t YOUR_USERNAME/rocmroute-zero:final .
docker push YOUR_USERNAME/rocmroute-zero:final
```

The build downloads the public Qwen weights into the image. Runtime does not download them.

## Clean-pull validation

```bash
docker image rm YOUR_USERNAME/rocmroute-zero:final
docker pull YOUR_USERNAME/rocmroute-zero:final

mkdir -p clean-input clean-output
cp evaluation/public_validation_tasks_flat.json clean-input/tasks.json

docker run --rm \
  --device /dev/kfd \
  --device /dev/dri \
  --group-add video \
  --ipc host \
  -v "$PWD/clean-input:/input:ro" \
  -v "$PWD/clean-output:/output" \
  YOUR_USERNAME/rocmroute-zero:final
```

Confirm `clean-output/results.json` contains exactly one non-empty answer per input task and only `task_id` and `answer` fields.

## Submission form

- Title: `ROCmRoute Zero`
- Upload `outputs/rocmroute-zero-deck/ROCmRoute_Zero_Submission_Deck.pdf`
- Upload the recorded demo video.
- Enter the exact public image tag used in the clean-pull test.
- Confirm the registry repository is public.
- Submit once; do not repeatedly resubmit while scoring is queued.
