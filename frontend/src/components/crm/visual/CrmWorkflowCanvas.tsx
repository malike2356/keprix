import dynamic from "next/dynamic";
import Typography from "@mui/material/Typography";

/** Route-split xyflow so contacts/settings do not pay for the graph library (514). */
const CrmWorkflowCanvas = dynamic(() => import("./CrmWorkflowCanvasClient"), {
  ssr: false,
  loading: () => <Typography color="text.secondary">Loading canvas...</Typography>,
});

export default CrmWorkflowCanvas;
