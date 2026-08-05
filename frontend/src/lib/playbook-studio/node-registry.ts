import BotIcon from "@mui/icons-material/SmartToy";
import BranchIcon from "@mui/icons-material/AccountTree";
import GlobeIcon from "@mui/icons-material/Public";
import PlayIcon from "@mui/icons-material/PlayArrow";
import UserCheckIcon from "@mui/icons-material/HowToReg";
import ForkRightIcon from "@mui/icons-material/ForkRight";
import DescriptionIcon from "@mui/icons-material/Description";
import ScheduleIcon from "@mui/icons-material/Schedule";
import type { SvgIconComponent } from "@mui/icons-material";
import type { StudioNodeData, StudioNodeType } from "@/lib/playbook-studio/canvas-types";

export type StudioNodeDefinition = {
  type: StudioNodeType;
  label: string;
  color: "default" | "primary" | "info" | "warning" | "secondary";
  icon: SvgIconComponent;
  defaults: StudioNodeData;
};

export const STUDIO_NODE_DEFINITIONS: StudioNodeDefinition[] = [
  {
    type: "trigger",
    label: "Trigger",
    color: "default",
    icon: PlayIcon,
    defaults: { label: "Trigger", description: "" },
  },
  {
    type: "agent_task",
    label: "LLM / Agent",
    color: "primary",
    icon: BotIcon,
    defaults: { label: "Agent task", prompt: "Describe the task", tools: [] },
  },
  {
    type: "http",
    label: "HTTP",
    color: "info",
    icon: GlobeIcon,
    defaults: { label: "HTTP request", url: "", method: "GET", headers: {}, body: "" },
  },
  {
    type: "condition",
    label: "Condition",
    color: "warning",
    icon: BranchIcon,
    defaults: {
      label: "Condition",
      expression: "risk_score > 70",
      trueLabel: "True",
      falseLabel: "False",
    },
  },
  {
    type: "human_approval",
    label: "Approval",
    color: "secondary",
    icon: UserCheckIcon,
    defaults: { label: "Approval", message: "Approve this step", risk: "medium", summary: "" },
  },
  {
    type: "parallel",
    label: "Parallel",
    color: "info",
    icon: ForkRightIcon,
    defaults: { label: "Parallel", tasks: [] },
  },
  {
    type: "artifact",
    label: "Artifact",
    color: "secondary",
    icon: DescriptionIcon,
    defaults: { label: "Artifact", name: "result", content: "" },
  },
  {
    type: "delay",
    label: "Delay",
    color: "warning",
    icon: ScheduleIcon,
    defaults: { label: "Delay", message: "Delay placeholder" },
  },
];

export function nodeDefinition(type: StudioNodeType): StudioNodeDefinition {
  return STUDIO_NODE_DEFINITIONS.find((item) => item.type === type) || STUDIO_NODE_DEFINITIONS[1];
}
