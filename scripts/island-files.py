#!/usr/bin/env python3
"""Explicit island file actions. Local reads and copies; no model or shell commands."""
import importlib.util
import json
import os
import ctypes
from pathlib import Path
from pathlib import PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import tarfile
import zipfile
import re
from urllib.parse import unquote, urlsplit
import warnings
from PIL import Image, ImageOps

TEXT = {".txt", ".md", ".json", ".py", ".qml", ".js", ".ts", ".rs", ".go", ".lua", ".sh", ".toml", ".yaml", ".yml", ".css", ".html", ".csv", ".log"}
IMAGES = {".png", ".jpg", ".jpeg", ".webp"}
Image.MAX_IMAGE_PIXELS = 25_000_000
warnings.simplefilter("error", Image.DecompressionBombWarning)


def inspect(value):
    url = urlsplit(value)
    if url.scheme and (url.scheme != "file" or url.netloc not in {"", "localhost"}):
        raise ValueError("Drop a local file.")
    original = Path(unquote(url.path) if url.scheme else value).expanduser()
    file = original.resolve()
    if original.is_symlink() or Path.home().resolve() not in file.parents or not file.is_file() or file.stat().st_size > 512_000_000:
        raise ValueError("Choose regular files inside your home folder, up to 512 MB each.")
    if any(part.startswith(".") for part in file.relative_to(Path.home().resolve()).parts) or file.suffix.lower() in {".key", ".pem"}:
        raise ValueError("Hidden and credential files cannot be processed.")
    suffix = file.suffix.lower()
    kind = "image" if suffix in IMAGES else "pdf" if suffix == ".pdf" else "text" if suffix in TEXT else "archive" if zipfile.is_zipfile(file) or tarfile.is_tarfile(file) else "file"
    data = dict(path=str(file), url=file.as_uri(), name=file.name, kind=kind, size=file.stat().st_size,
                readable=kind in {"pdf", "text"} or kind == "image" and bool(shutil.which("tesseract")),
                attachable=kind in {"pdf", "text", "image"} and file.stat().st_size <= 8_000_000)
    if kind == "image":
        with Image.open(file) as image:
            data.update(width=image.width, height=image.height)
            image.verify()
    return data


def output_folder():
    folder = Path.home()/"Documents"/"Luma"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    if folder.resolve() != folder:
        raise ValueError("Output folder must not be a symbolic link.")
    return folder


def publish(temp, name):
    """Hard-link publication is atomic and never overwrites an existing result."""
    folder = output_folder()
    for count in range(1000):
        output = folder/(Path(name).stem+("-"+str(count) if count else "")+Path(name).suffix)
        try:
            os.link(temp, output)
            return str(output)
        except FileExistsError:
            continue
    raise ValueError("Too many copies with this name.")


def compress(files):
    with tempfile.NamedTemporaryFile(dir=output_folder(), prefix=".luma-", suffix=".zip") as temp:
        used = set()
        with zipfile.ZipFile(temp.name, "w", zipfile.ZIP_DEFLATED, compresslevel=3) as archive:
            for file in files:
                name = file["name"]
                if name in used:
                    raise ValueError("Choose files with different names for this archive.")
                used.add(name)
                archive.write(file["path"], name)
        return publish(temp.name, (Path(files[0]["name"]).stem if len(files)==1 else "Files")+".zip")


def unpack(file):
    # Stage only regular entries; links, traversal, duplicate names and oversized archives fail before writes.
    folder = output_folder()
    source = Path(file["path"])
    archive = zipfile.ZipFile(source) if zipfile.is_zipfile(source) else tarfile.open(source)
    with archive:
        zipped = isinstance(archive, zipfile.ZipFile)
        entries = archive.infolist() if zipped else archive
        size, names, checked = 0, set(), []
        if zipped and len(entries)>10000:
            raise ValueError("Archive contains too many entries (maximum 10,000).")
        for index,entry in enumerate(entries):
            if index>=10000:
                raise ValueError("Archive contains too many entries (maximum 10,000).")
            name = entry.filename if zipped else entry.name
            path = PurePosixPath(name)
            directory = entry.is_dir() if zipped else entry.isdir()
            mode = entry.external_attr>>16 if zipped else 0
            if (not name or path.is_absolute() or ".." in path.parts or "\\" in name or "\x00" in name
                    or zipped and mode & 0o170000 not in {0, 0o100000, 0o040000}
                    or not zipped and not (entry.isfile() or directory)):
                raise ValueError("Archive has unsafe paths or special entries.")
            if str(path) in names:
                raise ValueError("Archive has duplicate paths.")
            names.add(str(path))
            size += entry.file_size if zipped else entry.size
            if size>512_000_000:
                raise ValueError("Extracted archive exceeds 512 MB.")
            checked.append((entry, path, directory))
        # Unique destination is also the staging area. Failed extraction removes only our new folder.
        destination = Path(tempfile.mkdtemp(dir=folder, prefix=source.stem+"-"))
        written = 0
        try:
            for entry, path, directory in checked:
                target = destination.joinpath(*path.parts)
                if directory:
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                reader = archive.open(entry) if zipped else archive.extractfile(entry)
                with reader, target.open("xb") as output:
                    while block := reader.read(1024*1024):
                        written += len(block)
                        if written>512_000_000:
                            raise ValueError("Extracted archive exceeds 512 MB.")
                        output.write(block)
            return str(destination)
        except Exception:
            shutil.rmtree(destination)
            raise


def merge(files):
    if len(files)<2 or any(file["kind"]!="pdf" for file in files):
        raise ValueError("Choose two or three PDFs to merge in their listed order.")
    with tempfile.TemporaryDirectory(dir=output_folder(), prefix=".merge-") as folder:
        output = Path(folder)/"Merged.pdf"
        subprocess.run(["pdfunite", *[file["path"] for file in files], str(output)], check=True, capture_output=True, timeout=60)
        return publish(output, "Merged.pdf")


def rename_plan(files, prefix):
    if not isinstance(prefix, str) or not re.fullmatch(r"[\w -]{1,64}", prefix.strip()) or not prefix.strip():
        raise ValueError("Use a name of 1–64 letters, numbers, spaces, underscores or hyphens.")
    rows = []
    for index, file in enumerate(files, 1):
        source = Path(file["path"])
        suffix = "".join(source.suffixes) if file["kind"]=="archive" else source.suffix
        name = prefix.strip()+("-"+str(index).zfill(2) if len(files)>1 else "")+suffix
        target = source.with_name(name)
        stat = source.stat()
        if target != source and target.exists():
            raise ValueError("A destination name already exists. Choose another name.")
        rows.append(dict(path=str(source), target=str(target), name=name, identity=[str(stat.st_dev),str(stat.st_ino),str(stat.st_mtime_ns),str(stat.st_size)]))
    return rows


def rename(files, prefix, approved):
    plan = rename_plan(files, prefix)
    if approved != plan:
        raise ValueError("Files changed since preview. Preview their names again.")
    # Linux renameat2 makes no-overwrite moves atomic; ordinary rename() can clobber a late arrival.
    libc = ctypes.CDLL(None, use_errno=True)
    move = getattr(libc, "renameat2", None)
    if move is None:
        raise ValueError("Safe rename is unavailable on this system.")
    move.argtypes = [ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.c_char_p,ctypes.c_uint]
    move.restype = ctypes.c_int
    def exclusive(source, target):
        if move(-100,os.fsencode(source),-100,os.fsencode(target),1):
            code = ctypes.get_errno()
            raise OSError(code,os.strerror(code))
    completed = []
    try:
        for row in plan:
            if row["path"]!=row["target"]:
                exclusive(row["path"],row["target"])
                completed.append(row)
    except OSError:
        for row in reversed(completed):
            try:
                exclusive(row["target"],row["path"])
            except OSError:
                # Never overwrite a new arrival during rollback; the original content stays at target.
                raise ValueError("Rename stopped. Some files remain at their previewed names; no files were overwritten.")
        raise ValueError("Rename stopped; original names restored.")
    return plan


def extract(file):
    if file["kind"] == "image":
        if not file["readable"]:
            raise ValueError("Install tesseract and tesseract-data-eng to copy text from images.")
        return subprocess.run(["tesseract", file["path"], "stdout", "-l", "eng"], capture_output=True, text=True, check=True, timeout=20).stdout
    if file["kind"] == "pdf":
        spec = importlib.util.spec_from_file_location("documents", Path(__file__).with_name("document-text.py"))
        documents = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(documents)
        return documents.read_pdf(file["path"], max_pages=40, limit=100000)["text"]
    with Path(file["path"]).open(encoding="utf-8", errors="replace") as stream:
        return stream.read(100001)


def export(file, width, fmt):
    folder = Path.home() / "Pictures" / "Luma"
    folder.mkdir(parents=True, exist_ok=True, mode=0o700)
    if folder.resolve()!=folder:
        raise ValueError("Output folder must not be a symbolic link.")
    suffix = {"PNG": ".png", "JPEG": ".jpg", "WEBP": ".webp"}[fmt]
    with Image.open(file["path"]) as original:
        image = ImageOps.exif_transpose(original)
        height = max(1, round(image.height * width / image.width))
        if width * height > Image.MAX_IMAGE_PIXELS:
            raise ValueError("Choose a smaller width; exported images can contain up to 25 million pixels.")
        if image.size != (width, height):
            image = image.resize((width, height), Image.Resampling.LANCZOS)
        if fmt == "JPEG":
            if "A" in image.getbands() or "transparency" in image.info:
                rgba = image.convert("RGBA")
                image = Image.new("RGB", rgba.size, "white")
                image.paste(rgba, mask=rgba.getchannel("A"))
            else:
                image = image.convert("RGB")
        with tempfile.NamedTemporaryFile(dir=folder, prefix=".luma-", suffix=suffix, delete=False) as stream:
            temp = Path(stream.name)
        try:
            image.save(temp, format=fmt, **({"quality": 95} if fmt != "PNG" else {}))
            stem = Path(file["path"]).stem + "-" + str(width)
            for count in range(1000):
                result = folder / (stem + ("-" + str(count) if count else "") + suffix)
                try:
                    os.link(temp, result)  # Exclusive creation: never overwrite a source or earlier export.
                    return str(result)
                except FileExistsError:
                    continue
            raise ValueError("Too many copies with that name. Rename the source first.")
        finally:
            temp.unlink(missing_ok=True)


def run(request):
    paths = request.get("paths")
    if not isinstance(paths, list) or not 1 <= len(paths) <= 3 or not all(isinstance(p, str) for p in paths):
        raise ValueError("Drop up to three files at once.")
    files = [inspect(value) for value in dict.fromkeys(paths)]
    operation = request.get("operation", "inspect")
    if operation == "inspect":
        return dict(files=files)
    if sum(file["size"] for file in files)>512_000_000:
        raise ValueError("Choose files totalling at most 512 MB.")
    if operation == "compress":
        return dict(files=files,status="Archive saved", outputs=[compress(files)])
    if operation == "unpack":
        if len(files)!=1 or files[0]["kind"]!="archive":
            raise ValueError("Choose one ZIP or tar archive.")
        return dict(files=files,status="Archive extracted", outputs=[unpack(files[0])])
    if operation == "merge":
        return dict(files=files,status="PDFs merged", outputs=[merge(files)])
    if operation == "rename-preview":
        return dict(plan=rename_plan(files,request.get("prefix")))
    if operation == "rename":
        rows = rename(files,request.get("prefix"),request.get("plan"))
        return dict(status="Renamed",files=[inspect(row["target"]) for row in rows],outputs=[row["target"] for row in rows])
    if operation == "extract":
        if not all(file["readable"] for file in files):
            raise ValueError("Choose text files, PDFs or images with OCR available.")
        text = "\n\n".join(extract(file).strip() for file in files).strip()
        if not text:
            raise ValueError("No readable text found.")
        subprocess.run(["wl-copy", "--type", "text/plain;charset=utf-8"], input=text[:100000], text=True, check=True, timeout=4)
        limit = " · first 100,000 characters" if len(text) > 100000 else " · PDF: up to 40 pages" if any(f["kind"] == "pdf" for f in files) else " · English OCR" if any(f["kind"] == "image" for f in files) else ""
        return dict(status="Text copied" + limit)
    if operation == "export":
        width, fmt = request.get("width"), request.get("format")
        if type(width) is not int or not 1 <= width <= 8192 or fmt not in {"PNG", "JPEG", "WEBP"} or any(f["kind"] != "image" for f in files):
            raise ValueError("Choose images, a width between 1 and 8192, and PNG, JPEG or WebP.")
        if any(width * max(1, round(f["height"] * width / f["width"])) > Image.MAX_IMAGE_PIXELS for f in files):
            raise ValueError("Choose a smaller width; exported images can contain up to 25 million pixels.")
        outputs = [export(file, width, fmt) for file in files]
        return dict(files=files,status="Saved " + ("image" if len(outputs) == 1 else str(len(outputs)) + " images"), outputs=outputs)
    raise ValueError("Unsupported file action.")


if __name__ == "__main__":
    try:
        print(json.dumps(dict(ok=True, **run(json.loads(sys.stdin.readline(64000))))), flush=True)
    except (ValueError, OSError, subprocess.SubprocessError, zipfile.BadZipFile, tarfile.TarError, Image.DecompressionBombError, Image.DecompressionBombWarning) as error:
        text = str(error) if isinstance(error, ValueError) else "Could not process this file. Check its format and installed tools."
        print(json.dumps(dict(ok=False, error=text)), flush=True)
        sys.exit(1)
