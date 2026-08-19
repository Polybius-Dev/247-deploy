#!/usr/bin/env python3
"""
split.py - Encode and split any file into GitHub-safe chunks.

Usage:
    python split.py <file> [--chunk-size KB] [--output-dir DIR] [--silent]

Outputs:
    Chunks ready to paste into GitHub Secrets (APP_CODE_1, APP_CODE_2, ...)
"""

import base64
import os
import sys
import argparse
import shutil
import re


DEFAULT_CHUNK_SIZE = 45  # KB, stays safely under GitHub's 48 KB secret limit
MAX_CHUNK_SIZE = 48      # KB, GitHub's hard limit per secret
TERMINAL_WIDTH = shutil.get_terminal_size().columns


def print_header(text):
    print("\n" + "=" * TERMINAL_WIDTH)
    print(text.center(TERMINAL_WIDTH))
    print("=" * TERMINAL_WIDTH + "\n")


def encode_file(file_path):
    """Read a file and return its base64-encoded string."""
    try:
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
        sys.exit(1)
    except PermissionError:
        print(f"Error: Permission denied reading '{file_path}'.")
        sys.exit(1)
    except Exception as e:
        print(f"Error reading file: {e}")
        sys.exit(1)


def split_encoded(encoded, chunk_size_bytes):
    """Split an encoded string into chunks of the given byte size."""
    return [encoded[i:i + chunk_size_bytes] for i in range(0, len(encoded), chunk_size_bytes)]


def write_chunks_to_files(chunks, output_dir, base_name):
    """Write chunks to individual files in the output directory."""
    os.makedirs(output_dir, exist_ok=True)
    paths = []
    for i, chunk in enumerate(chunks, 1):
        path = os.path.join(output_dir, f"{base_name}_chunk_{i}.txt")
        with open(path, "w") as f:
            f.write(chunk)
        paths.append(path)
    return paths


def write_summary_file(file_path, original_size, encoded_size, chunk_size, chunks, chunk_paths, output_dir, base_name):
    """Write a summary file with instructions for the user."""
    summary_path = os.path.join(output_dir, f"{base_name}_summary.txt")
    with open(summary_path, "w") as f:
        f.write("247-deploy Splitter Summary\n")
        f.write("=" * 60 + "\n\n")
        f.write(f"File: {file_path}\n")
        f.write(f"Original size: {original_size:,} bytes ({original_size / 1024:.2f} KB)\n")
        f.write(f"Encoded size: {encoded_size:,} bytes ({encoded_size / 1024:.2f} KB)\n")
        f.write(f"Chunk size: {chunk_size} KB\n")
        f.write(f"Total chunks: {len(chunks)}\n\n")

        f.write("Chunk files:\n")
        for path in chunk_paths:
            f.write(f"  {path}\n")
        f.write("\n")

        f.write("GitHub Secrets to create:\n")
        f.write("-" * 60 + "\n")
        for i, path in enumerate(chunk_paths, 1):
            f.write(f"  APP_CODE_{i}: (paste contents of {path})\n")
        f.write("-" * 60 + "\n\n")

        f.write("Quick commands (GitHub CLI):\n")
        f.write("-" * 60 + "\n")
        for i, path in enumerate(chunk_paths, 1):
            f.write(f"  gh secret set APP_CODE_{i} < {path}\n")
        f.write("-" * 60 + "\n\n")

        f.write("The workflow will automatically reassemble these chunks in order.\n")
    return summary_path


def main():
    parser = argparse.ArgumentParser(
        description="Encode and split any file into GitHub-safe chunks."
    )
    parser.add_argument("file", help="Path to the file to encode")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=DEFAULT_CHUNK_SIZE,
        help=f"Chunk size in KB (default: {DEFAULT_CHUNK_SIZE}, max: {MAX_CHUNK_SIZE})"
    )
    parser.add_argument(
        "--output-dir",
        default="chunks",
        help="Directory to save chunk files (default: chunks/)"
    )
    parser.add_argument(
        "--silent",
        action="store_true",
        help="Only print chunk files, no extra output"
    )
    args = parser.parse_args()

    # Validate chunk size
    if args.chunk_size > MAX_CHUNK_SIZE:
        print(f"Error: Chunk size cannot exceed {MAX_CHUNK_SIZE} KB (GitHub secret limit).")
        sys.exit(1)
    if args.chunk_size < 1:
        print("Error: Chunk size must be at least 1 KB.")
        sys.exit(1)

    chunk_size_bytes = args.chunk_size * 1024

    # Resolve file path
    file_path = os.path.abspath(args.file)
    if not os.path.isfile(file_path):
        print(f"Error: '{args.file}' is not a valid file.")
        sys.exit(1)

    file_size = os.path.getsize(file_path)
    if file_size == 0:
        print("Error: File is empty.")
        sys.exit(1)

    # Encode
    if not args.silent:
        print_header("247-deploy Splitter")
        print(f"File: {file_path}")
        print(f"Original size: {file_size:,} bytes ({file_size / 1024:.2f} KB)")

    encoded = encode_file(file_path)

    if not args.silent:
        print(f"Encoded size: {len(encoded):,} bytes ({len(encoded) / 1024:.2f} KB)")

    # Split
    chunks = split_encoded(encoded, chunk_size_bytes)
    total_chunks = len(chunks)

    if not args.silent:
        print(f"Chunk size: {args.chunk_size} KB")
        print(f"Total chunks: {total_chunks}")
        print()

    # Create a safe base name from the original file name (keeps extension)
    base_name = re.sub(r'[^\w\-\.]', '_', os.path.basename(file_path))

    # Write chunks to files
    chunk_paths = write_chunks_to_files(chunks, args.output_dir, base_name)

    # Write summary file only if not in silent mode
    if not args.silent:
        summary_path = write_summary_file(
            file_path, file_size, len(encoded), args.chunk_size, chunks, chunk_paths, args.output_dir, base_name
        )

        print("Chunks written to:")
        for path in chunk_paths:
            print(f"  {path}")
        print()

        print("Summary file written to:")
        print(f"  {summary_path}")
        print()

        print("GitHub Secrets to create:")
        print("-" * TERMINAL_WIDTH)
        for i, path in enumerate(chunk_paths, 1):
            print(f"  APP_CODE_{i}: (paste contents of {path})")
        print("-" * TERMINAL_WIDTH)
        print()

        print("Quick commands (GitHub CLI):")
        print("-" * TERMINAL_WIDTH)
        for i, path in enumerate(chunk_paths, 1):
            print(f'  gh secret set APP_CODE_{i} < {path}')
        print("-" * TERMINAL_WIDTH)
        print()

        print("The workflow will automatically reassemble these chunks in order.")
    else:
        # Silent mode: only output chunk paths
        for path in chunk_paths:
            print(path)


if __name__ == "__main__":
    main()
