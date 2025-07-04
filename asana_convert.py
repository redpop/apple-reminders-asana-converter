#!/usr/bin/env python3
"""
Apple Reminders JSON to Asana CSV Converter
Converts exported Apple Reminders JSON files to Asana CSV import format
"""

import json
import csv
import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import re


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='Converts Apple Reminders JSON files to Asana CSV format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert single file
  python asana_convert.py -f reminder.json -o output.csv
  
  # Convert all files in directory (single CSV)
  python asana_convert.py -d json/ -o asana_import.csv
  
  # Convert all files in directory (separate CSVs)
  python asana_convert.py -d json/ --separate
  
  # With assignee
  python asana_convert.py -d json/ -o asana_import.csv --assignee "john.doe@company.com"
  
  # Include completed tasks (default: only open tasks)
  python asana_convert.py -d json/ -o all_tasks.csv --include-completed
        """
    )
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-f', '--file', type=str, help='Single JSON file to convert')
    input_group.add_argument('-d', '--directory', type=str, help='Directory containing JSON files')
    
    parser.add_argument('-o', '--output', type=str, help='Output CSV file (default: asana_import.csv)')
    parser.add_argument('--separate', action='store_true', help='Create separate CSV files for each JSON')
    parser.add_argument('--assignee', type=str, help='Email address for assignee (e.g. john.doe@company.com)')
    parser.add_argument('--include-completed', action='store_true', help='Include completed tasks (default: only open tasks)')
    parser.add_argument('--dry-run', action='store_true', help='Test run without writing files')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    
    return parser.parse_args()


def format_date(date_string: str) -> str:
    """
    Converts Apple date format (ISO 8601) to Asana format (MM/DD/YYYY)
    """
    if not date_string:
        return ''
    
    try:
        # Parse ISO format with timezone
        dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
        # Return in US format MM/DD/YYYY
        return dt.strftime('%m/%d/%Y')
    except Exception as e:
        if args.verbose:
            print(f"Warning: Could not convert date '{date_string}': {e}")
        return ''


def map_priority(apple_priority: str) -> str:
    """Converts Apple priorities to Asana priorities (for global custom field)"""
    priority_map = {
        # German Apple Reminders
        'Ohne': 'Low',
        'Niedrig': 'Low', 
        'Mittel': 'Medium',
        'Hoch': 'High',
        # English Apple Reminders
        'None': 'Low',
        'Low': 'Low',
        'Medium': 'Medium', 
        'High': 'High',
        '': 'Low'  # Default
    }
    return priority_map.get(apple_priority, 'Low')


def extract_tags_from_title(title: str) -> Tuple[str, List[str]]:
    """
    Extracts tags from title (e.g. #mac #development)
    Returns cleaned title and list of tags
    """
    tags = re.findall(r'#(\w+)', title)
    clean_title = re.sub(r'\s*#\w+', '', title).strip()
    return clean_title, tags


def format_section(list_name: str) -> str:
    """
    Formats the list name as section for Asana CSV
    Removes colon at the end if present (Asana adds it automatically)
    """
    if not list_name:
        return ''
    
    # Remove colon at the end if present
    if list_name.endswith(':'):
        return list_name[:-1].strip()
    
    # Return the name unchanged
    return list_name


def convert_json_to_asana_row(json_data: Dict, default_assignee: Optional[str] = None) -> Dict:
    """
    Converts a single JSON row to Asana CSV format
    """
    # Extract tags from title
    title = json_data.get('Title', '')
    clean_title, tags = extract_tags_from_title(title)
    
    # Basic mapping - only required fields
    assignee_email = default_assignee or ''
    
    # Try to extract name from email if available
    assignee_name = ''
    if assignee_email:
        # Simple extraction: firstname.lastname@domain.com -> Firstname Lastname
        local_part = assignee_email.split('@')[0]
        if '.' in local_part:
            name_parts = local_part.split('.')
            assignee_name = ' '.join(part.capitalize() for part in name_parts)
        else:
            assignee_name = local_part.capitalize()
    
    row = {
        'Name': clean_title or title,  # If no tags, use original title
        'Description': json_data.get('Notes', ''),
        'Target Section': format_section(json_data.get('List', '')),  # As custom field
        'Assignee': assignee_name,
        'Assignee Email': assignee_email,
        'Due Date': format_date(json_data.get('Due Date', '')),
        'Tags': ', '.join(tags) if tags else '',  # Tags extracted from title
        'Priority': map_priority(json_data.get('Priority', ''))
    }
    
    # Tags are now in separate Tags field, not in Description
    
    return row


def write_csv_file(filepath: str, rows: List[Dict], dry_run: bool = False):
    """Writes the CSV file with converted data"""
    if dry_run:
        print(f"[DRY RUN] Would write {len(rows)} rows to {filepath}")
        return
    
    # Asana CSV header - uses existing Asana field names
    # "Priority" and "Target Section" are global custom fields
    # "Target Section" prevents the problem of duplicate sections during import
    fieldnames = [
        'Name', 'Description', 'Target Section', 'Assignee', 'Assignee Email',
        'Due Date', 'Tags', 'Priority'
    ]
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def process_single_file(json_path: str, output_path: str, default_assignee: Optional[str] = None, 
                       include_completed: bool = False, dry_run: bool = False, verbose: bool = False) -> bool:
    """
    Processes a single JSON file
    Returns True if successful, False on error
    """
    try:
        if verbose:
            print(f"Processing: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Skip completed tasks by default (unless explicitly requested)
        if not include_completed and json_data.get('Is Completed', False):
            if verbose:
                print(f"  ⏭ Skipping completed task: {json_data.get('Title', 'Unknown')}")
            return True  # Count as successful, but don't process
        
        # Convert to Asana format
        row = convert_json_to_asana_row(json_data, default_assignee)
        
        # Write CSV
        write_csv_file(output_path, [row], dry_run)
        
        if not dry_run and verbose:
            print(f"  ✓ Successfully converted to: {output_path}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"  ✗ Error: Invalid JSON in {json_path}: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error processing {json_path}: {e}")
        return False


def process_directory(directory: str, output_path: Optional[str], separate: bool,
                     default_assignee: Optional[str] = None, include_completed: bool = False,
                     dry_run: bool = False, verbose: bool = False) -> Tuple[int, int, int]:
    """
    Processes all JSON files in a directory
    Returns count of successful, failed and skipped conversions
    """
    json_files = list(Path(directory).glob('*.json'))
    
    if not json_files:
        print(f"No JSON files found in {directory}")
        return 0, 0, 0
    
    print(f"Found: {len(json_files)} JSON files")
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    all_rows = []
    
    for i, json_path in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] {json_path.name}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Skip completed tasks by default (unless explicitly requested)
            if not include_completed and json_data.get('Is Completed', False):
                print(f"  ⏭ Skipping completed task: {json_data.get('Title', 'Unknown')}")
                skipped_count += 1
                continue
            
            row = convert_json_to_asana_row(json_data, default_assignee)
            
            if separate:
                # Separate CSV for each file
                csv_name = json_path.stem + '_asana.csv'
                csv_path = json_path.parent / csv_name
                write_csv_file(str(csv_path), [row], dry_run)
                if verbose and not dry_run:
                    print(f"  ✓ Written to: {csv_path}")
            else:
                # Collect all rows for one large CSV
                all_rows.append(row)
            
            success_count += 1
            
        except json.JSONDecodeError as e:
            print(f"  ✗ Invalid JSON: {e}")
            error_count += 1
        except Exception as e:
            print(f"  ✗ Error: {e}")
            error_count += 1
    
    # If not separate, write all rows to one file
    if not separate and all_rows:
        output_file = output_path or 'asana_import.csv'
        write_csv_file(output_file, all_rows, dry_run)
        if not dry_run:
            print(f"\n✓ All {len(all_rows)} tasks written to {output_file}")
            print("\n💡 IMPORTANT NOTE:")
            print("   The CSV uses 'Target Section' as a custom field.")
            print("   Create a rule in Asana:")
            print("   'When Target Section = X, then move task to Section X'")
            print("   This prevents duplicate sections during import.")
    
    return success_count, error_count, skipped_count


def main():
    """Main function"""
    global args
    args = parse_arguments()
    
    print("Apple Reminders → Asana CSV Converter")
    print("=" * 40)
    
    if args.dry_run:
        print("[DRY RUN MODE - No files will be written]")
        print()
    
    if args.file:
        # Process single file
        output_path = args.output or 'asana_import.csv'
        success = process_single_file(
            args.file, output_path, args.assignee, 
            args.include_completed, args.dry_run, args.verbose
        )
        
        if success:
            print(f"\n✓ Conversion successful!")
            if not args.dry_run:
                print(f"CSV file created: {output_path}")
                print("\n💡 IMPORTANT NOTE:")
                print("   The CSV uses 'Target Section' as a custom field.")
                print("   Create a rule in Asana:")
                print("   'When Target Section = X, then move task to Section X'")
                print("   This prevents duplicate sections during import.")
        else:
            print("\n✗ Conversion failed!")
            sys.exit(1)
            
    else:
        # Process directory
        success, errors, skipped = process_directory(
            args.directory, args.output, args.separate,
            args.assignee, args.include_completed, args.dry_run, args.verbose
        )
        
        print("\n" + "=" * 40)
        print(f"Summary:")
        print(f"  ✓ Successful: {success} files")
        print(f"  ✗ Errors: {errors} files")
        if skipped > 0:
            print(f"  ⏭ Skipped: {skipped} completed tasks (use --include-completed to convert all)")
        
        if success == 0:
            sys.exit(1)


if __name__ == "__main__":
    main()