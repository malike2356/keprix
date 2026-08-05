"use client";

import Box from "@mui/material/Box";
import Button from "@mui/material/Button";
import Chip from "@mui/material/Chip";
import LinearProgress from "@mui/material/LinearProgress";
import MenuItem from "@mui/material/MenuItem";
import Paper from "@mui/material/Paper";
import Select from "@mui/material/Select";
import Slider from "@mui/material/Slider";
import Stack from "@mui/material/Stack";
import Typography from "@mui/material/Typography";
import FastForwardIcon from "@mui/icons-material/FastForward";
import FastRewindIcon from "@mui/icons-material/FastRewind";
import PauseIcon from "@mui/icons-material/Pause";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SkipNextIcon from "@mui/icons-material/SkipNext";
import SkipPreviousIcon from "@mui/icons-material/SkipPrevious";
import CloseIcon from "@mui/icons-material/Close";
import type { ReplayActivation, SessionReplayData } from "@/types/brain-replay";
import { useBrainReplayExport } from "@/components/brain/BrainReplayExport";

type ReplayControls = ReturnType<typeof import("@/hooks/useBrainReplay").useBrainReplay>;

type Props = {
  data: SessionReplayData;
  controls: ReplayControls;
  onClose: () => void;
};

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export default function BrainReplayTransport({ data, controls, onClose }: Props) {
  const exports = useBrainReplayExport(data);
  const progress = controls.totalSteps > 1 ? (controls.currentStep / (controls.totalSteps - 1)) * 100 : 0;
  const message = controls.currentMessage;
  const stepActivations: ReplayActivation[] = controls.currentActivations;

  return (
    <Paper variant="outlined" sx={{ maxHeight: 280, overflow: "auto" }}>
      <Stack spacing={1.25} sx={{ p: 1.5 }}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle2">
              Replaying: {data.session_title}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {formatDate(data.session_date)}
            </Typography>
          </Box>
          <Button size="small" startIcon={<CloseIcon />} onClick={onClose}>
            Close
          </Button>
        </Stack>

        {!data.has_brain_activity ? (
          <Typography color="warning.main">
            No brain activity recorded for this session.
          </Typography>
        ) : null}

        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
          <Button size="small" onClick={() => controls.jumpTo(0)} startIcon={<FastRewindIcon />}>Start</Button>
          <Button size="small" onClick={controls.stepBackward} startIcon={<SkipPreviousIcon />}>Back</Button>
          <Button
            size="small"
            variant="contained"
            onClick={controls.playing ? controls.pause : controls.play}
            startIcon={controls.playing ? <PauseIcon /> : <PlayArrowIcon />}
          >
            {controls.playing ? "Pause" : "Play"}
          </Button>
          <Button size="small" onClick={controls.stepForward} endIcon={<SkipNextIcon />}>Next</Button>
          <Button size="small" onClick={() => controls.jumpTo(controls.totalSteps - 1)} endIcon={<FastForwardIcon />}>End</Button>
          <Typography variant="caption" sx={{ px: 1 }}>
            Step {controls.currentStep + 1} / {controls.totalSteps}
          </Typography>
          <Select
            size="small"
            value={controls.speed}
            onChange={(event) => controls.setSpeed(Number(event.target.value) as 1 | 2 | 4)}
            sx={{ minWidth: 72 }}
          >
            <MenuItem value={1}>1x</MenuItem>
            <MenuItem value={2}>2x</MenuItem>
            <MenuItem value={4}>4x</MenuItem>
          </Select>
        </Stack>

        <Box>
          <LinearProgress variant="determinate" value={progress} sx={{ mb: 1, height: 8, borderRadius: 999 }} />
          <Slider
            size="small"
            value={controls.currentStep}
            min={0}
            max={Math.max(controls.totalSteps - 1, 0)}
            onChange={(_, value) => controls.jumpTo(Number(value))}
          />
        </Box>

        {message ? (
          <Box>
            <Typography variant="caption" color="text.secondary">Current turn</Typography>
            <Typography variant="body2">
              {message.role === "user" ? "User" : "Aiva"}: {message.content}
            </Typography>
          </Box>
        ) : null}

        <Box>
          <Typography variant="caption" color="text.secondary">Activated at this step</Typography>
          <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap sx={{ mt: 0.5 }}>
            {stepActivations.length === 0 ? (
              <Typography variant="body2" color="text.secondary">No activations at this step.</Typography>
            ) : (
              stepActivations.map((activation) => (
                <Chip
                  key={`${activation.node_kind}:${activation.node_id}:${activation.activated_at}`}
                  size="small"
                  label={`[${activation.node_kind}] ${activation.node_label} · ${activation.relation}${activation.confidence != null ? ` (${activation.confidence.toFixed(2)})` : ""}`}
                />
              ))
            )}
          </Stack>
        </Box>

        <Stack direction="row" spacing={1}>
          <Button size="small" variant="outlined" onClick={exports.exportTranscript}>
            Export transcript
          </Button>
          <Button size="small" variant="outlined" onClick={exports.exportActivationLog}>
            Export activation log
          </Button>
        </Stack>
      </Stack>
    </Paper>
  );
}
