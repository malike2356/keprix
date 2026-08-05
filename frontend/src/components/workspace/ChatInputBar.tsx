"use client";

import AttachFileIcon from "@mui/icons-material/AttachFile";
import CloseIcon from "@mui/icons-material/Close";
import MicIcon from "@mui/icons-material/Mic";
import MicOffIcon from "@mui/icons-material/MicOff";
import SendIcon from "@mui/icons-material/Send";
import StopIcon from "@mui/icons-material/Stop";
import Alert from "@mui/material/Alert";
import Box from "@mui/material/Box";
import Chip from "@mui/material/Chip";
import CircularProgress from "@mui/material/CircularProgress"; // @loading-contract-ignore button spinner
import IconButton from "@mui/material/IconButton";
import Popover from "@mui/material/Popover";
import TextField from "@mui/material/TextField";
import { alpha, keyframes, useTheme } from "@mui/material/styles";
import * as React from "react";
import ChatVoiceControl from "@/components/workspace/ChatVoiceControl";
import { useWebVoiceRecorder } from "@/hooks/useWebVoiceRecorder";
import { uploadChatFile } from "@/lib/workspace-api";

type AttachedFile = {
  id: string;
  filename: string;
};

type ChatInputBarProps = {
  onSend: (text: string, fileIds: string[]) => Promise<void> | void;
  onStop: () => void;
  isStreaming?: boolean;
};

const micPulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.55; }
`;

export default function ChatInputBar({ onSend, onStop, isStreaming = false }: ChatInputBarProps) {
  const theme = useTheme();
  const [value, setValue] = React.useState("");
  const [files, setFiles] = React.useState<AttachedFile[]>([]);
  const [voiceError, setVoiceError] = React.useState<string | null>(null);
  const inputRef = React.useRef<HTMLTextAreaElement | null>(null);
  const fileInputRef = React.useRef<HTMLInputElement | null>(null);
  const micButtonRef = React.useRef<HTMLButtonElement | null>(null);

  const { toggle, cancel, status, elapsedSeconds, sttAvailable } = useWebVoiceRecorder({
    enabled: !isStreaming,
    onTranscript: (text) => {
      setValue((prev) => (prev.trim() ? `${prev.trim()} ${text}` : text));
      inputRef.current?.focus();
    },
    onError: (msg) => setVoiceError(msg),
  });

  const isRecording = status === "recording";
  const isTranscribing = status === "transcribing";
  const micDisabled = isStreaming || !sttAvailable || isTranscribing;

  React.useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const submit = async () => {
    const trimmed = value.trim();
    if (!trimmed || isStreaming) return;
    await onSend(
      trimmed,
      files.map((file) => file.id),
    );
    setValue("");
    setFiles([]);
  };

  const onKeyDown = (event: React.KeyboardEvent) => {
    if (event.key === "Escape") {
      if (isRecording) {
        event.preventDefault();
        cancel();
        return;
      }
      setValue("");
      return;
    }
    if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === "m") {
      event.preventDefault();
      if (!micDisabled && !isTranscribing) {
        toggle();
      }
      return;
    }
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      if (!isStreaming) {
        void submit();
      }
    }
  };

  const onPickFiles = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const selected = Array.from(event.target.files || []);
    event.target.value = "";
    for (const file of selected) {
      const uploaded = await uploadChatFile(file);
      setFiles((prev) => [...prev, { id: uploaded.id, filename: uploaded.filename }]);
    }
  };

  const micAriaLabel = isTranscribing
    ? "Transcribing"
    : isRecording
      ? "Stop recording"
      : micDisabled
        ? "Voice input unavailable"
        : "Start voice input";

  return (
    <Box
      sx={{
        borderTop: 1,
        borderColor: "divider",
        p: 2,
        backdropFilter: "blur(12px)",
        bgcolor: alpha(theme.palette.background.default, 0.85),
      }}
    >
      <Box aria-live="polite" aria-atomic="true" sx={{ position: "absolute", width: 1, height: 1, overflow: "hidden", clip: "rect(0 0 0 0)" }}>
        {isRecording ? "Listening..." : null}
        {voiceError ? voiceError : null}
      </Box>
      {voiceError ? (
        <Alert severity="warning" onClose={() => setVoiceError(null)} sx={{ mb: 1 }}>
          {voiceError}
        </Alert>
      ) : null}
      {files.length > 0 ? (
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1, mb: 1 }}>
          {files.map((file) => (
            <Chip
              key={file.id}
              label={file.filename}
              onDelete={() => setFiles((prev) => prev.filter((item) => item.id !== file.id))}
              deleteIcon={<CloseIcon />}
            />
          ))}
        </Box>
      ) : null}
      <Box
        sx={{
          border: 1,
          borderColor: "divider",
          borderRadius: 2,
          bgcolor: "background.paper",
          p: 1,
        }}
      >
      <Box sx={{ display: "flex", alignItems: "flex-end", gap: 1 }}>
        <IconButton onClick={() => fileInputRef.current?.click()} aria-label="Attach file">
          <AttachFileIcon />
        </IconButton>
        <input ref={fileInputRef} type="file" hidden multiple onChange={onPickFiles} />
        <IconButton
          ref={micButtonRef}
          onClick={() => toggle()}
          disabled={micDisabled}
          aria-label={micAriaLabel}
          aria-pressed={isRecording ? true : undefined}
          color={isRecording ? "error" : "default"}
          sx={
            isRecording
              ? {
                  animation: `${micPulse} 1.2s ease-in-out infinite`,
                }
              : undefined
          }
        >
          {isTranscribing ? (
            <CircularProgress size={20} aria-hidden />
          ) : micDisabled ? (
            <MicOffIcon />
          ) : (
            <MicIcon />
          )}
        </IconButton>
        <Popover
          open={isRecording}
          anchorEl={micButtonRef.current}
          onClose={() => cancel()}
          anchorOrigin={{ vertical: "top", horizontal: "center" }}
          transformOrigin={{ vertical: "bottom", horizontal: "center" }}
          disableAutoFocus
          disableEnforceFocus
          slotProps={{
            paper: {
              sx: { p: 1.5, minWidth: 280 },
            },
          }}
        >
          <ChatVoiceControl
            isRecording={isRecording}
            elapsedSeconds={elapsedSeconds}
            disabled={micDisabled}
            onToggleRecording={() => toggle()}
          />
        </Popover>
        <TextField
          inputRef={inputRef}
          multiline
          minRows={1}
          maxRows={8}
          fullWidth
          variant="standard"
          placeholder="Message your agent..."
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={onKeyDown}
          InputProps={{ disableUnderline: true }}
        />
        <IconButton
          color="primary"
          onClick={() => (isStreaming ? onStop() : void submit())}
          disabled={!isStreaming && !value.trim()}
          aria-label={isStreaming ? "Stop" : "Send"}
        >
          {isStreaming ? <StopIcon /> : <SendIcon />}
        </IconButton>
      </Box>
      </Box>
    </Box>
  );
}
