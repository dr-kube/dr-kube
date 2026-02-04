"""
Decode Loki push payloads (protobuf or JSON) into log lines and labels.
"""

from __future__ import annotations

from functools import lru_cache
import re
from typing import Dict, List, Tuple

from google.protobuf import descriptor_pb2, descriptor_pool, message_factory, timestamp_pb2
from google.protobuf.message import DecodeError
from loguru import logger

try:
    import snappy  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    snappy = None


_LABEL_RE = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)="((?:\\\\.|[^"])*)"')


def decode_loki_push_request(req) -> Tuple[List[str], Dict[str, str]]:
    content_type = (req.headers.get("Content-Type") or "").lower()
    if "application/json" in content_type:
        data = req.get_json(silent=True)
        return _decode_loki_json(data)
    return _decode_loki_protobuf(req.get_data())


def _decode_loki_json(data: Dict[str, object]) -> Tuple[List[str], Dict[str, str]]:
    if not data:
        raise ValueError("missing JSON payload")

    streams = data.get("streams", [])
    if not streams:
        raise ValueError("missing streams in JSON payload")

    log_lines: List[str] = []
    metadata: Dict[str, str] = {}

    for stream in streams:
        labels = stream.get("stream", {})
        if isinstance(labels, dict):
            metadata.update({str(k): str(v) for k, v in labels.items()})
        values = stream.get("values", [])
        for entry in values:
            if isinstance(entry, list) and len(entry) >= 2:
                log_lines.append(entry[1])

    if not log_lines:
        raise ValueError("no log lines in JSON payload")

    return log_lines, metadata


def _decode_loki_protobuf(body: bytes) -> Tuple[List[str], Dict[str, str]]:
    if not body:
        raise ValueError("empty protobuf payload")

    raw = body
    if snappy is not None:
        try:
            raw = snappy.decompress(body)
        except Exception:
            raw = body
    else:
        logger.warning("python-snappy is not installed; skipping snappy decode")

    for use_int64 in (False, True):
        push_cls = _get_push_request_class(timestamp_as_int64=use_int64)
        msg = push_cls()
        try:
            msg.ParseFromString(raw)
        except DecodeError:
            continue
        if not msg.streams:
            continue
        return _extract_from_push_request(msg)

    raise ValueError("invalid Loki protobuf payload")


def _extract_from_push_request(push_request) -> Tuple[List[str], Dict[str, str]]:
    log_lines: List[str] = []
    metadata: Dict[str, str] = {}

    for stream in push_request.streams:
        metadata.update(_parse_labels(stream.labels))
        for entry in stream.entries:
            log_lines.append(entry.line)

    if not log_lines:
        raise ValueError("no log lines in protobuf payload")

    return log_lines, metadata


def _parse_labels(label_str: str) -> Dict[str, str]:
    if not label_str:
        return {}
    label_str = label_str.strip()
    if label_str.startswith("{") and label_str.endswith("}"):
        label_str = label_str[1:-1]
    labels: Dict[str, str] = {}
    for key, value in _LABEL_RE.findall(label_str):
        labels[key] = value.replace('\\"', '"')
    return labels


@lru_cache(maxsize=2)
def _get_push_request_class(timestamp_as_int64: bool):
    pool = descriptor_pool.DescriptorPool()
    if not timestamp_as_int64:
        pool.AddSerializedFile(timestamp_pb2.DESCRIPTOR.serialized_pb)

    file_proto = descriptor_pb2.FileDescriptorProto()
    file_proto.name = "logproto.proto"
    file_proto.package = "logproto"
    file_proto.syntax = "proto3"
    if not timestamp_as_int64:
        file_proto.dependency.append("google/protobuf/timestamp.proto")

    entry = file_proto.message_type.add()
    entry.name = "Entry"
    field = entry.field.add()
    field.name = "timestamp"
    field.number = 1
    field.label = field.LABEL_OPTIONAL
    if timestamp_as_int64:
        field.type = field.TYPE_INT64
    else:
        field.type = field.TYPE_MESSAGE
        field.type_name = ".google.protobuf.Timestamp"
    field = entry.field.add()
    field.name = "line"
    field.number = 2
    field.label = field.LABEL_OPTIONAL
    field.type = field.TYPE_STRING

    stream = file_proto.message_type.add()
    stream.name = "Stream"
    field = stream.field.add()
    field.name = "labels"
    field.number = 1
    field.label = field.LABEL_OPTIONAL
    field.type = field.TYPE_STRING
    field = stream.field.add()
    field.name = "entries"
    field.number = 2
    field.label = field.LABEL_REPEATED
    field.type = field.TYPE_MESSAGE
    field.type_name = ".logproto.Entry"

    push = file_proto.message_type.add()
    push.name = "PushRequest"
    field = push.field.add()
    field.name = "streams"
    field.number = 1
    field.label = field.LABEL_REPEATED
    field.type = field.TYPE_MESSAGE
    field.type_name = ".logproto.Stream"

    pool.Add(file_proto)
    desc = pool.FindMessageTypeByName("logproto.PushRequest")
    try:
        return message_factory.GetMessageClass(desc)
    except AttributeError:
        factory = message_factory.MessageFactory(pool)
        return factory.GetPrototype(desc)
