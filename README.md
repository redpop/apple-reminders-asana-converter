# Apple Reminders to Asana CSV Converter

A Python tool to convert Apple Reminders JSON exports to Asana-compatible CSV format for easy import and project management migration.

## Features

- ✅ **Single file or batch processing** - Convert one file or entire directories
- ✅ **Smart task filtering** - Skip completed tasks by default (configurable)
- ✅ **Tag extraction** - Automatically extracts hashtags from titles into separate tags field
- ✅ **Custom fields support** - Uses Asana custom fields to avoid duplicate sections
- ✅ **Date conversion** - Converts Apple's ISO format to Asana's MM/DD/YYYY format
- ✅ **Priority mapping** - Maps Apple priorities to Asana priority levels
- ✅ **Assignee support** - Optional assignee configuration with automatic name extraction
- ✅ **Dry run mode** - Preview conversions without creating files

## Prerequisites

- Python 3.6+
- Apple Reminders export in JSON format

## Installation

1. Clone this repository:

```bash
git clone https://github.com/yourusername/apple-reminders-asana-converter.git
cd apple-reminders-asana-converter
```

2. Install dependencies (optional, uses only Python standard library):

```bash
pip install -r requirements.txt
```

## How to Export from Apple Reminders

### Option 1: Built-in Export (macOS)

1. Open Apple Reminders on macOS
2. Select the list you want to export
3. Go to File → Export...
4. Choose JSON format
5. Save the file(s) to a folder

### Option 2: Using apple-reminders-exporter (Recommended)

For more comprehensive exports or if the built-in export doesn't work, use the [apple-reminders-exporter](https://github.com/Kylmakalle/apple-reminders-exporter) tool:

1. Install the exporter tool
2. Export all reminders to JSON format
3. Use the generated JSON files with this converter

## Usage

### Basic Examples

```bash
# Convert a single file
python asana_convert.py -f reminder.json -o output.csv

# Convert all JSON files in a directory to one CSV
python asana_convert.py -d json_files/ -o asana_import.csv

# Convert all files with separate CSV for each
python asana_convert.py -d json_files/ --separate

# Set assignee for all tasks
python asana_convert.py -d json_files/ -o tasks.csv --assignee "john.doe@company.com"

# Include completed tasks (default: skip completed)
python asana_convert.py -d json_files/ -o all_tasks.csv --include-completed

# Dry run (preview without creating files)
python asana_convert.py -d json_files/ --dry-run
```

### Command Line Options

| Option                | Description                                                  |
| --------------------- | ------------------------------------------------------------ |
| `-f, --file`          | Single JSON file to convert                                  |
| `-d, --directory`     | Directory containing JSON files                              |
| `-o, --output`        | Output CSV file name (default: asana_import.csv)             |
| `--separate`          | Create separate CSV for each JSON file                       |
| `--assignee`          | Email address for task assignee (e.g., john.doe@company.com) |
| `--include-completed` | Include completed tasks in export                            |
| `--dry-run`           | Preview conversion without creating files                    |
| `-v, --verbose`       | Detailed output during conversion                            |

## Setting Up Default Assignee

### Option 1: Command Line (Recommended)

```bash
python asana_convert.py -d json_files/ --assignee "your.email@company.com"
```

### Option 2: Modify Script (For Permanent Default)

Edit `asana_convert.py` and change line 121:

```python
assignee_email = default_assignee or 'your.email@company.com'
```

## Asana Import Configuration

### Required Custom Fields in Asana

Before importing, create these **global custom fields** in your Asana workspace:

1. **Priority**

   - Type: Single-select dropdown
   - Options: Low, Medium, High

2. **Target Section**
   - Type: Text field
   - Used to avoid duplicate sections during import

### Setting Up Asana Rules (Important!)

To automatically organize tasks into sections, create this rule in Asana:

1. Go to your project → Rules → Create Rule
2. **Trigger:** "When custom field changes"
3. **Condition:** "Target Section is set to any value"
4. **Action:** "Move task to section with same value as Target Section"

This prevents Asana from creating duplicate sections during CSV import.

## CSV Output Format

The generated CSV contains these fields:

| Field          | Description                               |
| -------------- | ----------------------------------------- |
| Name           | Task title (cleaned of hashtags)          |
| Description    | Task notes/description                    |
| Target Section | Target section (custom field)             |
| Assignee       | Assignee name (auto-extracted from email) |
| Assignee Email | Assignee email address                    |
| Due Date       | Due date in MM/DD/YYYY format             |
| Tags           | Hashtags extracted from title             |
| Priority       | Priority level (Low/Medium/High)           |

## Data Processing Details

### Tag Extraction

Hashtags in titles like `"Website update #webdev #urgent"` become:

- **Name:** "Website update"
- **Tags:** "webdev, urgent"

### Priority Mapping

| Apple Priority (German) | Apple Priority (English) | Asana Priority |
| ----------------------- | ------------------------ | -------------- |
| Ohne                    | None                     | Low            |
| Niedrig                 | Low                      | Low            |
| Mittel                  | Medium                   | Medium         |
| Hoch                    | High                     | High           |

### Date Conversion

- **Apple:** `2025-12-31T23:59:59Z`
- **Asana:** `12/31/2025`

## Troubleshooting

### "No JSON files found"

- Ensure your JSON files have `.json` extension
- Check the directory path is correct

### "Invalid JSON" errors

- Verify the JSON files are valid Apple Reminders exports
- Some files might be corrupted during export

### Asana import shows duplicate sections

- Make sure you created the "Target Section" custom field
- Set up the Asana rule as described above

### Special characters in file names

- The script handles Unicode characters automatically
- No action needed for German umlauts or special characters

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test with sample data
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Run with `--verbose` flag for detailed output
3. Try `--dry-run` to preview the conversion
4. Create an issue on GitHub with sample data (anonymized)
