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
  # Convert bulk JSON file (from Backup Shortcut for Reminders)
  python asana_convert.py -f reminders_export.json -o output.csv --asana-language de
  
  # Convert with custom assignee
  python asana_convert.py -f reminders_export.json -o asana_tasks.csv --assignee "user@example.com"
  
  # Convert with German localization
  python asana_convert.py -f reminders_export.json -o tasks_de.csv --asana-language de --assignee "user@example.com"
        """
    )
    
    parser.add_argument('-f', '--file', type=str, required=True, help='JSON file to convert (bulk format from Backup Shortcut)')
    parser.add_argument('-o', '--output', type=str, help='Output CSV file (default: asana_import.csv)')
    parser.add_argument('--assignee', type=str, help='Email address for assignee (e.g. john.doe@company.com)')
    parser.add_argument('--include-completed', action='store_true', help='Include completed tasks (default: only open tasks)')
    parser.add_argument('--asana-language', type=str, choices=['en', 'de'], default='en', help='Language for Asana field names and values (en/de, default: en)')
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


def map_priority(apple_priority: str, language: str = 'en') -> str:
    """Converts Apple priorities to Asana priorities (for global custom field)"""
    # First map Apple to standard priority
    priority_map = {
        # German Apple Reminders (Backup Shortcut format)
        'Ohne': '',  # None/No priority - leave empty
        'Gering': 'Low',
        'Niedrig': 'Low', 
        'Mittel': 'Medium',
        'Hoch': 'High',
        # English Apple Reminders (apple-reminders-exporter format)
        'None': '',  # None/No priority - leave empty
        'Low': 'Low',
        'Medium': 'Medium', 
        'High': 'High',
        '': ''  # Empty - leave empty
    }
    
    standard_priority = priority_map.get(apple_priority, '')
    
    # Convert to target language
    if language == 'de':
        german_map = {
            'Low': 'Niedrig',
            'Medium': 'Mittel',
            'High': 'Hoch',
            '': ''  # Empty stays empty
        }
        return german_map.get(standard_priority, '')
    else:
        return standard_priority


def get_asana_fieldnames(language: str = 'en') -> List[str]:
    """Returns Asana CSV fieldnames in specified language"""
    # Use format with Parent task field for subtasks support
    # Removed "Assignee" and "Projects" fields per user request
    if language == 'de':
        return [
            'Name', 'Assignee Email', 'Due Date', 'Tags', 'Notes', 
            'Section/Column', 'Parent task', 'Priorität'
        ]
    else:
        return [
            'Name', 'Assignee Email', 'Due Date', 'Tags', 'Notes',
            'Section/Column', 'Parent task', 'Priority'
        ]


def extract_tags_from_title(title: str) -> Tuple[str, List[str]]:
    """
    Extracts tags from title (e.g. #mac #development)
    Returns cleaned title and list of tags
    """
    tags = re.findall(r'#(\w+)', title)
    clean_title = re.sub(r'\s*#\w+', '', title).strip()
    return clean_title, tags


def combine_tags(hashtags: List[str], native_tags: List[str]) -> List[str]:
    """
    Combines hashtags from title with native tags array, removing duplicates
    Returns merged list of unique tags
    """
    all_tags = hashtags + native_tags
    # Remove duplicates while preserving order
    seen = set()
    unique_tags = []
    for tag in all_tags:
        if tag.lower() not in seen:
            seen.add(tag.lower())
            unique_tags.append(tag)
    return unique_tags


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


def detect_json_format(json_data: Dict) -> str:
    """
    Detects the format of the JSON data
    Returns 'bulk' for {"reminders": [...]} format or 'single' for individual reminder
    """
    if 'reminders' in json_data and isinstance(json_data['reminders'], list):
        return 'bulk'
    elif 'Title' in json_data or 'title' in json_data:
        return 'single'
    else:
        return 'unknown'


def convert_json_to_asana_row(json_data: Dict, default_assignee: Optional[str] = None) -> Dict:
    """
    Converts a single JSON row to Asana CSV format
    Supports both old format (apple-reminders-exporter) and new format (Backup Shortcut)
    """
    # Detect format and normalize field access
    is_old_format = 'Title' in json_data  # Old format uses capitalized keys
    
    # Extract title and handle both formats
    if is_old_format:
        title = json_data.get('Title', '')
        notes = json_data.get('Notes', '')
        list_name = json_data.get('List', '')
        due_date = json_data.get('Due Date', '')
        priority = json_data.get('Priority', '')
        is_completed = json_data.get('Is Completed', False)
        native_tags = []  # Old format doesn't have native tags
    else:
        title = json_data.get('title', '')
        notes = json_data.get('notes', '')
        list_name = json_data.get('list', '')
        due_date = json_data.get('due_date', '')
        priority = json_data.get('prio', '')
        is_completed = json_data.get('done', '') == 'Ja'  # German: "Ja" = Yes
        native_tags = json_data.get('tags', [])
    
    # Extract hashtags from title
    clean_title, hashtags = extract_tags_from_title(title)
    
    # Combine hashtags and native tags
    all_tags = combine_tags(hashtags, native_tags)
    
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
        'Description': notes,
        'Target Section': format_section(list_name),  # As custom field
        'Assignee': assignee_name,
        'Assignee Email': assignee_email,
        'Due Date': format_date(due_date),
        'Tags': ', '.join(all_tags) if all_tags else '',  # Combined tags (will be imported as "Tags (importiert)")
        'Priority': map_priority(priority)
    }
    
    # Add additional fields for new format if available
    if not is_old_format:
        # Additional metadata we could include in description or custom fields
        additional_info = []
        if json_data.get('flagged', '') == 'Ja':
            additional_info.append('⭐ Flagged')
        if json_data.get('has_reminder', '') == 'Ja':
            additional_info.append('🔔 Has Reminder')
        if json_data.get('reminder_location'):
            additional_info.append(f'📍 Location: {json_data.get("reminder_location")}')
        if json_data.get('url'):
            additional_info.append(f'🔗 URL: {json_data.get("url")}')
        if json_data.get('subtasks'):
            subtask_count = len(json_data.get('subtasks', []))
            additional_info.append(f'📝 {subtask_count} subtasks')
        
        # Append additional info to description if present
        if additional_info:
            if row['Description']:
                row['Description'] += '\n\n' + '\n'.join(additional_info)
            else:
                row['Description'] = '\n'.join(additional_info)
    
    return row


def write_csv_file(filepath: str, rows: List[Dict], dry_run: bool = False, language: str = 'en'):
    """Writes the CSV file with converted data in Asana format"""
    if dry_run:
        print(f"[DRY RUN] Would write {len(rows)} rows to {filepath}")
        return
    
    # Always use Asana-compatible format with subtasks support
    fieldnames = get_asana_fieldnames(language)
    encoding = 'utf-8-sig'  # BOM for Excel compatibility
    
    with open(filepath, 'w', newline='', encoding=encoding) as csvfile:
        # Use QUOTE_ALL for better Asana compatibility (like in their exports)
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_ALL)
        writer.writeheader()
        writer.writerows(rows)


def convert_to_asana_format(reminders: List[Dict], default_assignee: Optional[str] = None, 
                           language: str = 'en') -> List[Dict]:
    """
    Converts reminders to Asana-compatible format with subtasks support
    Returns list of rows including main tasks and subtasks
    """
    asana_rows = []
    task_id_counter = 1210720000000000  # Start with a reasonable ID
    
    for reminder in reminders:
        # Get basic task info
        is_old_format = 'Title' in reminder
        if is_old_format:
            title = reminder.get('Title', '')
            notes = reminder.get('Notes', '')
            list_name = reminder.get('List', '')
            due_date = reminder.get('Due Date', '')
            priority = reminder.get('Priority', '')
            native_tags = []
            subtasks = []
        else:
            title = reminder.get('title', '')
            notes = reminder.get('notes', '')
            list_name = reminder.get('list', '')
            due_date = reminder.get('due_date', '')
            priority = reminder.get('prio', '')
            native_tags = reminder.get('tags', [])
            subtasks = reminder.get('subtasks', [])
        
        # Extract hashtags and clean title
        clean_title, hashtags = extract_tags_from_title(title)
        all_tags = combine_tags(hashtags, native_tags)
        
        # Prepare assignee info
        assignee_email = default_assignee or ''
        assignee_name = ''
        if assignee_email:
            local_part = assignee_email.split('@')[0]
            if '.' in local_part:
                name_parts = local_part.split('.')
                assignee_name = ' '.join(part.capitalize() for part in name_parts)
            else:
                assignee_name = local_part.capitalize()
        
        # Priority field name depends on language
        priority_field = 'Priorität' if language == 'de' else 'Priority'
        
        # Main task row with Parent task field for subtasks support
        # Removed "Assignee" and "Projects" fields per user request
        main_task = {
            'Name': clean_title or title,
            'Assignee Email': assignee_email,
            'Due Date': format_date(due_date),
            'Tags': ', '.join(all_tags) if all_tags else '',  # Will be imported as "Tags (importiert)" for manual mapping
            'Notes': notes,
            'Section/Column': format_section(list_name),
            'Parent task': '',  # Empty for main tasks
            priority_field: map_priority(priority, language)
        }
        
        # Add enhanced metadata to notes for new format
        if not is_old_format:
            additional_info = []
            if reminder.get('flagged', '') == 'Ja':
                additional_info.append('⭐ Flagged')
            if reminder.get('has_reminder', '') == 'Ja':
                additional_info.append('🔔 Has Reminder')
            if reminder.get('reminder_location'):
                additional_info.append(f'📍 Location: {reminder.get("reminder_location")}')
            if reminder.get('url'):
                additional_info.append(f'🔗 URL: {reminder.get("url")}')
            
            if additional_info:
                if main_task['Notes']:
                    main_task['Notes'] += '\n\n' + '\n'.join(additional_info)
                else:
                    main_task['Notes'] = '\n'.join(additional_info)
        
        asana_rows.append(main_task)
        task_id_counter += 1
        
        # Add subtasks as separate rows with proper Asana format
        for subtask in subtasks:
            # Extract subtask details (subtasks have all the same fields as main tasks)
            subtask_due_date = subtask.get('due_date', '')
            subtask_priority = subtask.get('prio', '')
            subtask_tags = subtask.get('tags', [])
            
            # Extract hashtags from subtask title if any
            subtask_clean_title, subtask_hashtags = extract_tags_from_title(subtask.get('title', 'Untitled Subtask'))
            subtask_all_tags = combine_tags(subtask_hashtags, subtask_tags)
            
            # Create subtask row with full support for all fields
            subtask_row = {
                'Name': subtask_clean_title or subtask.get('title', 'Untitled Subtask'),
                'Assignee Email': assignee_email,
                'Due Date': format_date(subtask_due_date),  # Support subtask due dates
                'Tags': ', '.join(subtask_all_tags) if subtask_all_tags else '',  # Support subtask tags
                'Notes': subtask.get('notes', ''),
                'Section/Column': '',  # Subtasks don't have sections
                'Parent task': clean_title or title,  # Reference to parent task by name
                priority_field: map_priority(subtask_priority, language)  # Support subtask priorities
            }
            
            # Add enhanced metadata for subtasks too (if not old format)
            if not is_old_format:
                subtask_additional_info = []
                if subtask.get('flagged', '') == 'Ja':
                    subtask_additional_info.append('⭐ Flagged')
                if subtask.get('has_reminder', '') == 'Ja':
                    subtask_additional_info.append('🔔 Has Reminder')
                if subtask.get('reminder_location'):
                    subtask_additional_info.append(f'📍 Location: {subtask.get("reminder_location")}')
                if subtask.get('url'):
                    subtask_additional_info.append(f'🔗 URL: {subtask.get("url")}')
                
                if subtask_additional_info:
                    if subtask_row['Notes']:
                        subtask_row['Notes'] += '\\n\\n' + '\\n'.join(subtask_additional_info)
                    else:
                        subtask_row['Notes'] = '\\n'.join(subtask_additional_info)
            
            asana_rows.append(subtask_row)
            task_id_counter += 1
    
    return asana_rows


def process_bulk_json(json_data: Dict, default_assignee: Optional[str] = None, 
                      include_completed: bool = False, verbose: bool = False) -> List[Dict]:
    """
    Processes bulk JSON format with {"reminders": [...]} structure
    Returns list of converted Asana rows
    """
    if 'reminders' not in json_data:
        raise ValueError("Bulk JSON must contain 'reminders' array")
    
    reminders = json_data['reminders']
    converted_rows = []
    skipped_count = 0
    
    for i, reminder in enumerate(reminders, 1):
        # Check completion status based on format
        is_completed = False
        title = ''
        
        if 'Title' in reminder:  # Old format
            is_completed = reminder.get('Is Completed', False)
            title = reminder.get('Title', 'Unknown')
        else:  # New format
            is_completed = reminder.get('done', '') == 'Ja'
            title = reminder.get('title', 'Unknown')
        
        # Skip completed tasks by default (unless explicitly requested)
        if not include_completed and is_completed:
            if verbose:
                print(f"  ⏭ Skipping completed task [{i}/{len(reminders)}]: {title}")
            skipped_count += 1
            continue
        
        # Convert to Asana format
        row = convert_json_to_asana_row(reminder, default_assignee)
        converted_rows.append(row)
        
        if verbose:
            print(f"  ✓ Converted [{i}/{len(reminders)}]: {title}")
    
    if verbose and skipped_count > 0:
        print(f"  📊 Processed {len(converted_rows)} tasks, skipped {skipped_count} completed tasks")
    
    return converted_rows


def process_single_file(json_path: str, output_path: str, default_assignee: Optional[str] = None, 
                       include_completed: bool = False, dry_run: bool = False, verbose: bool = False,
                       asana_format: bool = True, asana_language: str = 'en') -> bool:
    """
    Processes a single JSON file (supports both single reminder and bulk formats)
    Always uses Asana format with subtasks support
    Returns True if successful, False on error
    """
    try:
        if verbose:
            print(f"Processing: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Detect format
        format_type = detect_json_format(json_data)
        
        if format_type == 'bulk':
            # Process bulk JSON with multiple reminders
            if verbose:
                print(f"  📦 Detected bulk format with {len(json_data.get('reminders', []))} reminders")
            
            # Filter reminders based on completion status
            filtered_reminders = []
            skipped_count = 0
            
            for i, reminder in enumerate(json_data['reminders'], 1):
                # Check completion status
                is_completed = False
                title = ''
                
                if 'Title' in reminder:  # Old format
                    is_completed = reminder.get('Is Completed', False)
                    title = reminder.get('Title', 'Unknown')
                else:  # New format
                    is_completed = reminder.get('done', '') == 'Ja'
                    title = reminder.get('title', 'Unknown')
                
                # Skip completed tasks by default (unless explicitly requested)
                if not include_completed and is_completed:
                    if verbose:
                        print(f"  ⏭ Skipping completed task [{i}/{len(json_data['reminders'])}]: {title}")
                    skipped_count += 1
                    continue
                
                filtered_reminders.append(reminder)
                
                if verbose:
                    print(f"  ✓ Converted [{i}/{len(json_data['reminders'])}]: {title}")
            
            if not filtered_reminders:
                if verbose:
                    print(f"  ℹ️ No tasks to process (all completed and --include-completed not set)")
                return True
            
            if verbose and skipped_count > 0:
                print(f"  📊 Processed {len(filtered_reminders)} tasks, skipped {skipped_count} completed tasks")
            
            # Convert to Asana format with subtasks
            if verbose:
                print(f"  🔄 Converting to Asana format with subtasks...")
            
            asana_rows = convert_to_asana_format(filtered_reminders, default_assignee, asana_language)
            write_csv_file(output_path, asana_rows, dry_run, language=asana_language)
            
            if not dry_run and verbose:
                print(f"  ✓ Successfully converted {len(asana_rows)} tasks to: {output_path}")
        
        elif format_type == 'single':
            # Process single reminder
            # Check completion status based on format
            is_completed = False
            title = ''
            
            if 'Title' in json_data:  # Old format
                is_completed = json_data.get('Is Completed', False)
                title = json_data.get('Title', 'Unknown')
            else:  # New format single reminder
                is_completed = json_data.get('done', '') == 'Ja'
                title = json_data.get('title', 'Unknown')
            
            # Skip completed tasks by default (unless explicitly requested)
            if not include_completed and is_completed:
                if verbose:
                    print(f"  ⏭ Skipping completed task: {title}")
                return True  # Count as successful, but don't process
            
            # Convert to Asana format with subtasks
            if verbose:
                print(f"  🔄 Converting to Asana format with subtasks...")
            
            asana_rows = convert_to_asana_format([json_data], default_assignee, asana_language)
            write_csv_file(output_path, asana_rows, dry_run, language=asana_language)
            
            if not dry_run and verbose:
                print(f"  ✓ Successfully converted {len(asana_rows)} tasks to: {output_path}")
        
        else:
            print(f"  ✗ Unknown JSON format in {json_path}")
            return False
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"  ✗ Error: Invalid JSON in {json_path}: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Error processing {json_path}: {e}")
        return False




def main():
    """Main function"""
    global args
    args = parse_arguments()
    
    print("Apple Reminders → Asana CSV Converter")
    print("=" * 40)
    
    if args.dry_run:
        print("[DRY RUN MODE - No files will be written]")
        print()
    
    # Process single file with Asana format (always default now)
    output_path = args.output or 'asana_import.csv'
    success = process_single_file(
        args.file, output_path, args.assignee, 
        args.include_completed, args.dry_run, args.verbose,
        asana_format=True, asana_language=args.asana_language
    )
    
    if success:
        print(f"\n✓ Conversion successful!")
        if not args.dry_run:
            print(f"CSV file created: {output_path}")
            print("\n💡 Import the CSV into Asana:")
            print("   1. Create/use an Import project in Asana")
            print("   2. Add Priority/Priorität custom field to the project")
            print("   3. Import CSV - subtasks will nest automatically")
    else:
        print("\n✗ Conversion failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()