#!/usr/bin/env python3
"""
Job Fit Analysis CLI

Analyzes how well a portfolio aligns with a job description.
Compares portfolio evaluation results against job requirements and generates
detailed fit reports in JSON and text formats.

Usage:
    python job_fit_analysis.py \
        --evaluation-json portfolio_evaluation_results.json \
        --jd-file job_description.txt \
        --output-prefix job_fit_report
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from portfolio_fit.job_fit import analyze_job_fit, save_job_fit_report

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

def parse_arguments() -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        description="Analyze portfolio-to-job fit from evaluation JSON and job description.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python job_fit_analysis.py \
    --evaluation-json eval.json \
    --jd-file job_description.txt

  python job_fit_analysis.py \
    --evaluation-json eval.json \
    --jd-file job_description.txt \
    --output-prefix my_analysis
        """,
    )
    parser.add_argument(
        "--evaluation-json",
        type=str,
        required=True,
        help="Path to portfolio_evaluation_*.json",
    )
    parser.add_argument(
        "--jd-file",
        type=str,
        required=True,
        help="Path to job description text file",
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default="job_fit_report",
        help="Output prefix for JSON/TXT reports (default: job_fit_report)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose logging (DEBUG level)",
    )
    return parser.parse_args()

def load_evaluation(path: Path) -> List[Dict[str, Any]]:
    """
    Load and validate portfolio evaluation JSON file.
    
    Args:
        path: Path to evaluation JSON file
        
    Returns:
        List of evaluation dictionaries
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file format is invalid
        json.JSONDecodeError: If JSON parsing fails
    """
    if not path.exists():
        raise FileNotFoundError(f"Evaluation JSON not found: {path}")
    
    if path.suffix != ".json":
        logger.warning(f"File has unexpected extension: {path.suffix}, expected .json")
    
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in {path}: {e}")
    
    if not isinstance(data, list):
        raise ValueError(
            f"Evaluation JSON must contain a list, got {type(data).__name__}"
        )
    
    if not data:
        raise ValueError("Evaluation JSON is empty, no data to analyze")
    
    # Filter to only dict items
    valid_items = [item for item in data if isinstance(item, dict)]
    if len(valid_items) < len(data):
        skipped = len(data) - len(valid_items)
        logger.warning(f"Skipped {skipped} non-dict items in evaluation JSON")
    
    return valid_items

def load_job_description(path: Path) -> str:
    """
    Load and validate job description text file.
    
    Args:
        path: Path to job description file
        
    Returns:
        Job description text
        
    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not path.exists():
        raise FileNotFoundError(f"Job description file not found: {path}")
    
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        raise ValueError(f"Failed to read job description file: {e}")
    
    if not text.strip():
        raise ValueError("Job description file is empty")
    
    return text

def validate_output_path(prefix: str) -> Path:
    """
    Validate and prepare output path.
    
    Args:
        prefix: Output file prefix
        
    Returns:
        Validated output path
        
    Raises:
        ValueError: If path is invalid or not writable
    """
    output_path = Path(prefix).parent
    
    # Create parent directory if it doesn't exist
    try:
        output_path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ValueError(f"Cannot create output directory {output_path}: {e}")
    
    # Check if directory is writable
    if not output_path.exists() or not output_path.is_dir():
        raise ValueError(f"Output path is not a directory: {output_path}")
    
    return Path(prefix)

def print_summary(report: Dict[str, Any]) -> None:
    """
    Print job fit analysis summary to stdout.
    
    Args:
        report: Job fit analysis report dictionary
    """
    print(
        "\n" + "=" * 70
        + "\nJob Fit Analysis Summary\n"
        + "=" * 70
    )
    print(
        f"Overall Fit Score: {report['fit_score_percent']}% "
        f"({report['fit_category']})"
    )
    print(
        f"Must-Have Coverage: {report['must_have_coverage_percent']}%"
    )
    print(
        f"Nice-to-Have Coverage: {report['nice_to_have_coverage_percent']}%"
    )
    print("=" * 70 + "\n")

def analyze_job_fit_workflow(
    evaluation_json_path: str,
    jd_file_path: str,
    output_prefix: str = "job_fit_report",
) -> Dict[str, Any]:
    """
    Execute the complete job fit analysis workflow.
    
    Args:
        evaluation_json_path: Path to evaluation JSON file
        jd_file_path: Path to job description file
        output_prefix: Output file prefix
        
    Returns:
        Job fit analysis report
        
    Raises:
        FileNotFoundError: If input files don't exist
        ValueError: If input validation fails
    """
    eval_path = Path(evaluation_json_path)
    jd_path = Path(jd_file_path)
    
    logger.info(f"Loading evaluation from: {eval_path}")
    evaluation_results = load_evaluation(eval_path)
    logger.info(f"Loaded {len(evaluation_results)} portfolio items")
    
    logger.info(f"Loading job description from: {jd_path}")
    jd_text = load_job_description(jd_path)
    logger.info(f"Job description loaded ({len(jd_text)} characters)")
    
    logger.info("Validating output path...")
    validate_output_path(output_prefix)
    
    logger.info("Analyzing job fit...")
    report = analyze_job_fit(evaluation_results, jd_text)
    
    logger.info("Saving reports...")
    json_path, txt_path = save_job_fit_report(report, output_prefix)
    
    logger.info(f"Job fit JSON saved to: {json_path}")
    logger.info(f"Job fit TXT saved to: {txt_path}")
    
    return report

def main() -> int:
    """
    Main entry point for job fit analysis.
    
    Returns:
        Exit code (0 for success, 1 for failure)
    """
    args = parse_arguments()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    try:
        report = analyze_job_fit_workflow(
            evaluation_json_path=args.evaluation_json,
            jd_file_path=args.jd_file,
            output_prefix=args.output_prefix,
        )
        
        print_summary(report)
        logger.info("Job fit analysis completed successfully")
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1
        
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1
        
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
