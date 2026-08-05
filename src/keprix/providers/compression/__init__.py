"""Token compression pipeline: RTK request compression + Caveman decompression.

Average savings: 15-95%, typically ~42% on tool-heavy agent sessions.
All compression is opt-in and non-breaking.
"""

from .rtk import RTKCompressor, CompressedRequest
from .caveman import CavemanDecompressor
from .compressor import CompressionPipeline
from .context_dedup import ContextDeduplicator
from .tool_output_summary import ToolOutputSummariser
from .token_counter import count_tokens, estimate_tokens

__all__ = [
    "RTKCompressor",
    "CompressedRequest",
    "CavemanDecompressor",
    "CompressionPipeline",
    "ContextDeduplicator",
    "ToolOutputSummariser",
    "count_tokens",
    "estimate_tokens",
]
