from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .schemas import InputEnvelope


class OMSInputHub:
    """Uniform input entry for WeChat messages and files."""

    def accept_text(
        self,
        text: str,
        *,
        source: str = "wechat",
        group: str | None = None,
        sender: str | None = None,
        received_at: str | None = None,
    ) -> InputEnvelope:
        return InputEnvelope.from_text(
            text,
            source=source,
            channel="wechat_text" if source == "wechat" else "text",
            wechat_group=group,
            sender=sender,
            received_at=received_at,
        )

    def accept_file(
        self,
        file_path: str | Path,
        *,
        source: str = "wechat",
        group: str | None = None,
        sender: str | None = None,
        received_at: str | None = None,
    ) -> InputEnvelope:
        return InputEnvelope.from_file(
            file_path,
            source=source,
            channel="wechat_file" if source == "wechat" else "file",
            wechat_group=group,
            sender=sender,
            received_at=received_at,
        )

    def accept_directory(self, input_dir: str | Path) -> Iterable[InputEnvelope]:
        root = Path(input_dir)
        for path in sorted(p for p in root.rglob("*") if p.is_file()):
            yield self.accept_file(path)

