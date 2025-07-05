#!/usr/bin/env python
"""
Test suite for Apple Reminders to Asana CSV Converter
"""

import unittest
import json
import csv
import tempfile
import os
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, mock_open
import sys

# Import the module we're testing - add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
import asana_convert


class TestDateFormatting(unittest.TestCase):
    """Test date formatting functions"""
    
    def test_format_date_valid_iso(self):
        """Test formatting valid ISO 8601 dates"""
        test_date = "2025-03-15T09:00:00Z"
        result = asana_convert.format_date(test_date)
        self.assertEqual(result, "03/15/2025")
    
    def test_format_date_with_timezone(self):
        """Test formatting dates with timezone info"""
        test_date = "2025-12-31T23:59:59+00:00"
        result = asana_convert.format_date(test_date)
        self.assertEqual(result, "12/31/2025")
    
    def test_format_date_empty_string(self):
        """Test formatting empty date string"""
        result = asana_convert.format_date("")
        self.assertEqual(result, "")
    
    def test_format_date_none(self):
        """Test formatting None date"""
        result = asana_convert.format_date(None)
        self.assertEqual(result, "")
    
    def test_format_date_invalid_format(self):
        """Test formatting invalid date format"""
        # Set up the global args variable to have verbose=True
        original_args = getattr(asana_convert, 'args', None)
        
        # Create a mock args object
        class MockArgs:
            verbose = True
        
        asana_convert.args = MockArgs()
        
        try:
            with patch('builtins.print') as mock_print:
                result = asana_convert.format_date("invalid-date")
                self.assertEqual(result, "")
                mock_print.assert_called()
        finally:
            # Restore original args
            if original_args is not None:
                asana_convert.args = original_args
            elif hasattr(asana_convert, 'args'):
                delattr(asana_convert, 'args')


class TestPriorityMapping(unittest.TestCase):
    """Test priority mapping functions"""
    
    def test_map_priority_german(self):
        """Test German priority mapping"""
        self.assertEqual(asana_convert.map_priority("Ohne"), "Low")
        self.assertEqual(asana_convert.map_priority("Niedrig"), "Low")
        self.assertEqual(asana_convert.map_priority("Mittel"), "Medium")
        self.assertEqual(asana_convert.map_priority("Hoch"), "High")
    
    def test_map_priority_english(self):
        """Test English priority mapping"""
        self.assertEqual(asana_convert.map_priority("None"), "Low")
        self.assertEqual(asana_convert.map_priority("Low"), "Low")
        self.assertEqual(asana_convert.map_priority("Medium"), "Medium")
        self.assertEqual(asana_convert.map_priority("High"), "High")
    
    def test_map_priority_empty(self):
        """Test empty priority"""
        self.assertEqual(asana_convert.map_priority(""), "Low")
    
    def test_map_priority_unknown(self):
        """Test unknown priority defaults to Low"""
        self.assertEqual(asana_convert.map_priority("Unknown"), "Low")


class TestTagExtraction(unittest.TestCase):
    """Test tag extraction from titles"""
    
    def test_extract_tags_single_tag(self):
        """Test extracting single tag from title"""
        title = "Website update #webdev"
        clean_title, tags = asana_convert.extract_tags_from_title(title)
        self.assertEqual(clean_title, "Website update")
        self.assertEqual(tags, ["webdev"])
    
    def test_extract_tags_multiple_tags(self):
        """Test extracting multiple tags from title"""
        title = "Website redesign #webdev #design #urgent"
        clean_title, tags = asana_convert.extract_tags_from_title(title)
        self.assertEqual(clean_title, "Website redesign")
        self.assertEqual(tags, ["webdev", "design", "urgent"])
    
    def test_extract_tags_no_tags(self):
        """Test title without tags"""
        title = "Simple task without tags"
        clean_title, tags = asana_convert.extract_tags_from_title(title)
        self.assertEqual(clean_title, "Simple task without tags")
        self.assertEqual(tags, [])
    
    def test_extract_tags_empty_title(self):
        """Test empty title"""
        title = ""
        clean_title, tags = asana_convert.extract_tags_from_title(title)
        self.assertEqual(clean_title, "")
        self.assertEqual(tags, [])
    
    def test_extract_tags_with_spaces(self):
        """Test tag extraction with various spacing"""
        title = "Task #tag1  #tag2   #tag3"
        clean_title, tags = asana_convert.extract_tags_from_title(title)
        self.assertEqual(clean_title, "Task")
        self.assertEqual(tags, ["tag1", "tag2", "tag3"])


class TestSectionFormatting(unittest.TestCase):
    """Test section name formatting"""
    
    def test_format_section_with_colon(self):
        """Test removing colon from section name"""
        result = asana_convert.format_section("Work Projects:")
        self.assertEqual(result, "Work Projects")
    
    def test_format_section_without_colon(self):
        """Test section name without colon"""
        result = asana_convert.format_section("Personal")
        self.assertEqual(result, "Personal")
    
    def test_format_section_empty(self):
        """Test empty section name"""
        result = asana_convert.format_section("")
        self.assertEqual(result, "")
    
    def test_format_section_none(self):
        """Test None section name"""
        result = asana_convert.format_section(None)
        self.assertEqual(result, "")


class TestJsonToAsanaConversion(unittest.TestCase):
    """Test JSON to Asana row conversion"""
    
    def test_convert_basic_task(self):
        """Test converting basic task data"""
        json_data = {
            "Title": "Buy groceries",
            "Notes": "Weekly grocery shopping",
            "List": "Personal",
            "Due Date": "2025-02-08T18:00:00Z",
            "Priority": "Low",
            "Is Completed": False
        }
        
        result = asana_convert.convert_json_to_asana_row(json_data)
        
        self.assertEqual(result["Name"], "Buy groceries")
        self.assertEqual(result["Description"], "Weekly grocery shopping")
        self.assertEqual(result["Target Section"], "Personal")
        self.assertEqual(result["Due Date"], "02/08/2025")
        self.assertEqual(result["Priority"], "Low")
        self.assertEqual(result["Tags"], "")
    
    def test_convert_task_with_tags(self):
        """Test converting task with hashtags"""
        json_data = {
            "Title": "Website redesign #webdev #design #urgent",
            "Notes": "Update the company website",
            "List": "Work Projects",
            "Due Date": "2025-03-15T09:00:00Z",
            "Priority": "High",
            "Is Completed": False
        }
        
        result = asana_convert.convert_json_to_asana_row(json_data)
        
        self.assertEqual(result["Name"], "Website redesign")
        self.assertEqual(result["Tags"], "webdev, design, urgent")
        self.assertEqual(result["Target Section"], "Work Projects")
        self.assertEqual(result["Priority"], "High")
    
    def test_convert_task_with_assignee(self):
        """Test converting task with assignee"""
        json_data = {
            "Title": "Test task",
            "Notes": "",
            "List": "Work",
            "Due Date": "",
            "Priority": "",
            "Is Completed": False
        }
        
        result = asana_convert.convert_json_to_asana_row(json_data, "john.doe@company.com")
        
        self.assertEqual(result["Assignee"], "John Doe")
        self.assertEqual(result["Assignee Email"], "john.doe@company.com")
    
    def test_convert_task_assignee_simple_email(self):
        """Test converting task with simple email (no dots)"""
        json_data = {
            "Title": "Test task",
            "Notes": "",
            "List": "Work",
            "Due Date": "",
            "Priority": "",
            "Is Completed": False
        }
        
        result = asana_convert.convert_json_to_asana_row(json_data, "admin@company.com")
        
        self.assertEqual(result["Assignee"], "Admin")
        self.assertEqual(result["Assignee Email"], "admin@company.com")
    
    def test_convert_task_missing_fields(self):
        """Test converting task with missing fields"""
        json_data = {}
        
        result = asana_convert.convert_json_to_asana_row(json_data)
        
        self.assertEqual(result["Name"], "")
        self.assertEqual(result["Description"], "")
        self.assertEqual(result["Target Section"], "")
        self.assertEqual(result["Due Date"], "")
        self.assertEqual(result["Priority"], "Low")
        self.assertEqual(result["Tags"], "")


class TestCSVWriting(unittest.TestCase):
    """Test CSV file writing"""
    
    def test_write_csv_file_dry_run(self):
        """Test dry run mode doesn't write files"""
        rows = [{"Name": "Test", "Description": "Test desc"}]
        
        with patch('builtins.print') as mock_print:
            asana_convert.write_csv_file("test.csv", rows, dry_run=True)
            mock_print.assert_called_with("[DRY RUN] Would write 1 rows to test.csv")
    
    def test_write_csv_file_actual(self):
        """Test actual CSV file writing"""
        rows = [
            {
                "Name": "Test Task",
                "Description": "Test description",
                "Target Section": "Work",
                "Assignee": "John Doe",
                "Assignee Email": "john@example.com",
                "Due Date": "03/15/2025",
                "Tags": "test, example",
                "Priority": "High"
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            asana_convert.write_csv_file(tmp_path, rows, dry_run=False)
            
            # Verify file was written correctly
            with open(tmp_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                written_rows = list(reader)
                
            self.assertEqual(len(written_rows), 1)
            self.assertEqual(written_rows[0]["Name"], "Test Task")
            self.assertEqual(written_rows[0]["Priority"], "High")
            
        finally:
            os.unlink(tmp_path)


class TestFileProcessing(unittest.TestCase):
    """Test file processing functions"""
    
    def test_process_single_file_completed_task_skip(self):
        """Test skipping completed tasks by default"""
        json_data = {
            "Title": "Completed task",
            "Is Completed": True
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_json:
            json.dump(json_data, tmp_json)
            tmp_json_path = tmp_json.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_csv:
            tmp_csv_path = tmp_csv.name
        
        try:
            result = asana_convert.process_single_file(
                tmp_json_path, tmp_csv_path, 
                include_completed=False, verbose=True
            )
            
            self.assertTrue(result)
            # CSV file should not be created or should be empty when task is skipped
            if os.path.exists(tmp_csv_path):
                with open(tmp_csv_path, 'r') as f:
                    content = f.read().strip()
                    # File should be empty (no header written when no data to process)
                    self.assertEqual(content, "")
                
        finally:
            os.unlink(tmp_json_path)
            os.unlink(tmp_csv_path)
    
    def test_process_single_file_completed_task_include(self):
        """Test including completed tasks when requested"""
        json_data = {
            "Title": "Completed task",
            "Notes": "This task is done",
            "List": "Personal",
            "Is Completed": True,
            "Priority": "Medium"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_json:
            json.dump(json_data, tmp_json)
            tmp_json_path = tmp_json.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_csv:
            tmp_csv_path = tmp_csv.name
        
        try:
            result = asana_convert.process_single_file(
                tmp_json_path, tmp_csv_path, 
                include_completed=True
            )
            
            self.assertTrue(result)
            # CSV should contain the task
            with open(tmp_csv_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["Name"], "Completed task")
                
        finally:
            os.unlink(tmp_json_path)
            os.unlink(tmp_csv_path)
    
    def test_process_single_file_invalid_json(self):
        """Test handling invalid JSON files"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_json:
            tmp_json.write("invalid json content")
            tmp_json_path = tmp_json.name
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp_csv:
            tmp_csv_path = tmp_csv.name
        
        try:
            with patch('builtins.print') as mock_print:
                result = asana_convert.process_single_file(
                    tmp_json_path, tmp_csv_path
                )
                
            self.assertFalse(result)
            mock_print.assert_called()
            
        finally:
            os.unlink(tmp_json_path)
            os.unlink(tmp_csv_path)


class TestArgumentParsing(unittest.TestCase):
    """Test command line argument parsing"""
    
    def test_parse_arguments_file_mode(self):
        """Test parsing arguments for single file mode"""
        test_args = ['-f', 'input.json', '-o', 'output.csv']
        
        with patch.object(sys, 'argv', ['asana_convert.py'] + test_args):
            args = asana_convert.parse_arguments()
            
        self.assertEqual(args.file, 'input.json')
        self.assertEqual(args.output, 'output.csv')
        self.assertIsNone(args.directory)
        self.assertFalse(args.separate)
        self.assertFalse(args.include_completed)
        self.assertFalse(args.dry_run)
        self.assertFalse(args.verbose)
    
    def test_parse_arguments_directory_mode(self):
        """Test parsing arguments for directory mode"""
        test_args = ['-d', 'json_files/', '--separate', '--verbose', '--assignee', 'user@example.com']
        
        with patch.object(sys, 'argv', ['asana_convert.py'] + test_args):
            args = asana_convert.parse_arguments()
            
        self.assertEqual(args.directory, 'json_files/')
        self.assertTrue(args.separate)
        self.assertTrue(args.verbose)
        self.assertEqual(args.assignee, 'user@example.com')
        self.assertIsNone(args.file)


class TestProcessDirectory(unittest.TestCase):
    """Test directory processing functionality"""
    
    def test_process_directory_no_json_files(self):
        """Test processing directory with no JSON files"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create a non-JSON file
            with open(os.path.join(tmp_dir, 'not_json.txt'), 'w') as f:
                f.write("This is not a JSON file")
            
            with patch('builtins.print') as mock_print:
                success, errors, skipped = asana_convert.process_directory(
                    tmp_dir, 'output.csv', False
                )
                
            self.assertEqual(success, 0)
            self.assertEqual(errors, 0)
            self.assertEqual(skipped, 0)
            mock_print.assert_called_with(f"No JSON files found in {tmp_dir}")
    
    def test_process_directory_with_json_files(self):
        """Test processing directory with valid JSON files"""
        with tempfile.TemporaryDirectory() as tmp_dir:
            # Create test JSON files
            json_data1 = {
                "Title": "Task 1",
                "Notes": "First task",
                "List": "Work",
                "Is Completed": False
            }
            json_data2 = {
                "Title": "Task 2", 
                "Notes": "Second task",
                "List": "Personal",
                "Is Completed": False
            }
            
            with open(os.path.join(tmp_dir, 'task1.json'), 'w') as f:
                json.dump(json_data1, f)
            with open(os.path.join(tmp_dir, 'task2.json'), 'w') as f:
                json.dump(json_data2, f)
            
            output_path = os.path.join(tmp_dir, 'output.csv')
            
            success, errors, skipped = asana_convert.process_directory(
                tmp_dir, output_path, False
            )
            
            self.assertEqual(success, 2)
            self.assertEqual(errors, 0)
            self.assertEqual(skipped, 0)
            
            # Verify CSV was created with both tasks
            with open(output_path, 'r') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                self.assertEqual(len(rows), 2)


class TestTagCombining(unittest.TestCase):
    """Test tag combining functionality"""
    
    def test_combine_tags_no_duplicates(self):
        """Test combining tags without duplicates"""
        hashtags = ['webdev', 'urgent']
        native_tags = ['development', 'project']
        result = asana_convert.combine_tags(hashtags, native_tags)
        self.assertEqual(result, ['webdev', 'urgent', 'development', 'project'])
    
    def test_combine_tags_with_duplicates(self):
        """Test combining tags with case-insensitive deduplication"""
        hashtags = ['webdev', 'urgent']
        native_tags = ['development', 'WEBDEV', 'project']
        result = asana_convert.combine_tags(hashtags, native_tags)
        self.assertEqual(result, ['webdev', 'urgent', 'development', 'project'])
    
    def test_combine_tags_empty_lists(self):
        """Test combining empty tag lists"""
        result = asana_convert.combine_tags([], [])
        self.assertEqual(result, [])
    
    def test_combine_tags_one_empty(self):
        """Test combining when one list is empty"""
        hashtags = ['webdev', 'urgent']
        result1 = asana_convert.combine_tags(hashtags, [])
        result2 = asana_convert.combine_tags([], hashtags)
        self.assertEqual(result1, ['webdev', 'urgent'])
        self.assertEqual(result2, ['webdev', 'urgent'])


class TestJsonFormatDetection(unittest.TestCase):
    """Test JSON format detection"""
    
    def test_detect_bulk_format(self):
        """Test detection of bulk JSON format"""
        json_data = {"reminders": [{"title": "test"}]}
        result = asana_convert.detect_json_format(json_data)
        self.assertEqual(result, "bulk")
    
    def test_detect_single_format_old(self):
        """Test detection of single format (old apple-reminders-exporter)"""
        json_data = {"Title": "test", "Notes": "description"}
        result = asana_convert.detect_json_format(json_data)
        self.assertEqual(result, "single")
    
    def test_detect_single_format_new(self):
        """Test detection of single format (new backup shortcut)"""
        json_data = {"title": "test", "notes": "description"}
        result = asana_convert.detect_json_format(json_data)
        self.assertEqual(result, "single")
    
    def test_detect_unknown_format(self):
        """Test detection of unknown format"""
        json_data = {"unknown": "data"}
        result = asana_convert.detect_json_format(json_data)
        self.assertEqual(result, "unknown")


class TestBulkJsonProcessing(unittest.TestCase):
    """Test bulk JSON processing functionality"""
    
    def test_process_bulk_json_new_format(self):
        """Test processing bulk JSON with new format"""
        json_data = {
            "reminders": [
                {
                    "title": "Task 1 #tag1",
                    "notes": "Description 1",
                    "list": "Work",
                    "prio": "Hoch",
                    "done": "Nein",
                    "tags": ["native1"],
                    "flagged": "Ja",
                    "has_reminder": "Nein"
                },
                {
                    "title": "Task 2",
                    "notes": "Description 2", 
                    "list": "Personal",
                    "prio": "Mittel",
                    "done": "Ja",  # Completed task
                    "tags": []
                }
            ]
        }
        
        # Test without including completed
        rows = asana_convert.process_bulk_json(json_data, include_completed=False)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Name"], "Task 1")
        self.assertEqual(rows[0]["Tags"], "tag1,native1")
        self.assertEqual(rows[0]["Priority"], "High")
        self.assertIn("⭐ Flagged", rows[0]["Description"])
        
        # Test with including completed
        rows = asana_convert.process_bulk_json(json_data, include_completed=True)
        self.assertEqual(len(rows), 2)
    
    def test_process_bulk_json_old_format(self):
        """Test processing bulk JSON with old format mixed in"""
        json_data = {
            "reminders": [
                {
                    "Title": "Old Format Task",
                    "Notes": "Old description",
                    "List": "Work",
                    "Priority": "High",
                    "Is Completed": False
                }
            ]
        }
        
        rows = asana_convert.process_bulk_json(json_data)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["Name"], "Old Format Task")
        self.assertEqual(rows[0]["Priority"], "High")


class TestEnhancedConversion(unittest.TestCase):
    """Test enhanced JSON to Asana conversion"""
    
    def test_convert_new_format_with_metadata(self):
        """Test converting new format with all metadata fields"""
        json_data = {
            "title": "Enhanced Task #work #urgent",
            "notes": "Base description",
            "list": "Projects",
            "prio": "Hoch",
            "done": "Nein",
            "tags": ["native", "project"],
            "flagged": "Ja",
            "has_reminder": "Ja",
            "reminder_location": "Office",
            "url": "https://example.com",
            "subtasks": [{"title": "Sub 1"}, {"title": "Sub 2"}]
        }
        
        result = asana_convert.convert_json_to_asana_row(json_data)
        
        self.assertEqual(result["Name"], "Enhanced Task")
        self.assertEqual(result["Tags"], "work,urgent,native,project")
        self.assertEqual(result["Priority"], "High")
        self.assertEqual(result["Target Section"], "Projects")
        
        # Check additional metadata in description
        description = result["Description"]
        self.assertIn("Base description", description)
        self.assertIn("⭐ Flagged", description)
        self.assertIn("🔔 Has Reminder", description)
        self.assertIn("📍 Location: Office", description)
        self.assertIn("🔗 URL: https://example.com", description)
        self.assertIn("📝 2 subtasks", description)
    
    def test_convert_backward_compatibility(self):
        """Test that old format still works"""
        json_data = {
            "Title": "Old Task #legacy",
            "Notes": "Old description",
            "List": "Work",
            "Priority": "Medium",
            "Is Completed": False
        }
        
        result = asana_convert.convert_json_to_asana_row(json_data)
        
        self.assertEqual(result["Name"], "Old Task")
        self.assertEqual(result["Tags"], "legacy")
        self.assertEqual(result["Priority"], "Medium")
        self.assertEqual(result["Description"], "Old description")


class TestNewPriorityMapping(unittest.TestCase):
    """Test enhanced priority mapping"""
    
    def test_map_priority_german_backup_format(self):
        """Test German priority mapping for Backup Shortcut format"""
        self.assertEqual(asana_convert.map_priority("Ohne"), "Low")
        self.assertEqual(asana_convert.map_priority("Gering"), "Low")
        self.assertEqual(asana_convert.map_priority("Mittel"), "Medium")
        self.assertEqual(asana_convert.map_priority("Hoch"), "High")


if __name__ == '__main__':
    unittest.main()