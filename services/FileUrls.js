.pragma library

// Encode path components while preserving the file URL's directory separators.
function fromPath(path) {
    return path ? "file://" + path.split("/").map(encodeURIComponent).join("/") : "";
}
