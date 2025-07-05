# Apple Reminders to Asana CSV Converter

A Python tool to convert bulk Apple Reminders JSON exports to Asana-compatible CSV format with native subtasks support. Designed for seamless migration from Apple Reminders to Asana.

## Features

- ✅ **Bulk JSON processing** - Process hundreds of reminders in one file
- ✅ **Advanced subtasks** - Full feature parity with main tasks (due dates, priorities, tags)
- ✅ **Automatic deduplication** - Removes duplicate tasks during conversion
- ✅ **Localization support** - German and English field names/priorities
- ✅ **Smart task filtering** - Skip completed tasks by default (configurable)
- ✅ **Enhanced metadata** - Preserves flags, locations, URLs, reminders
- ✅ **Tag extraction** - Hashtags from titles + native tags combined
- ✅ **Priority mapping** - Maps German/English priorities to Asana values
- ✅ **Assignee support** - Automatic name extraction from email
- ✅ **Dry run mode** - Preview conversions without creating files

## Prerequisites

### 1. Export Tool (Required)

You need to export your Apple Reminders using the **"Backup Shortcut for Reminders"** iOS app:

- **Download:** [Backup Shortcut for Reminders](https://www.icloud.com/shortcuts/f79f09bed78347f0a378560ecd0e4f05)
- **Tutorial:** [Complete guide in German](https://janpedia.de/2024/09/16/backup-von-apple-erinnerungen-und-notizen-erstellen/)

This shortcut exports all your reminders as a single comprehensive JSON file with:

- All reminder lists and tasks
- Subtasks and nested structure
- Rich metadata (flags, locations, URLs, etc.)
- Native tags and priorities
- Complete task history

### 2. Python Environment

- Python 3.6+ (uses only standard library, no external dependencies)

## Installation

```bash
git clone https://github.com/yourusername/apple-reminders-asana-converter.git
cd apple-reminders-asana-converter
```

## Usage

### Recommended Workflow

```bash
# German Asana with subtasks (recommended)
python asana_convert.py -f reminders_export.json -o output.csv \
  --asana-language de \
  --assignee "your.email@example.com"

# English Asana with subtasks
python asana_convert.py -f reminders_export.json -o output.csv \
  --assignee "your.email@example.com"

# Include completed tasks
python asana_convert.py -f reminders_export.json -o all_tasks.csv \
  --include-completed

# Preview without creating files
python asana_convert.py -f reminders_export.json \
  --dry-run -v
```

### Command Line Options

| Option                     | Description                                                  |
| -------------------------- | ------------------------------------------------------------ |
| `-f, --file`               | JSON file to convert (bulk format from Backup Shortcut)      |
| `-o, --output`             | Output CSV file (default: asana_import.csv)                  |
| `--asana-language {en,de}` | Language for field names and priorities (en/de, default: en) |
| `--assignee`               | Email address for task assignee                              |
| `--include-completed`      | Include completed tasks in export                            |
| `--no-deduplicate`         | Disable automatic deduplication of tasks                     |
| `--dry-run`                | Preview conversion without creating files                    |
| `-v, --verbose`            | Detailed output during conversion                            |

## Asana Setup and Import

### Step 1: Create Global Custom Fields

**For German Asana:**

- Field name: **"Priorität"**
- Type: Dropdown
- Options: "Niedrig", "Mittel", "Hoch"

**For English Asana:**

- Field name: **"Priority"**
- Type: Dropdown
- Options: "Low", "Medium", "High"

### Step 2: Recommended Import Workflow

1. **Create an "Import" project** in Asana for testing
2. **Add the Priority/Priorität custom field** to this project
3. **Import the CSV** into the Import project
4. **Review tasks and subtasks** - they should nest automatically
5. **Move tasks** to final destination projects
6. **Clean up** the Import project for future use

### Step 3: Import in Asana

1. Open Asana → Navigate to your Import project
2. Three-dots menu → "Import" → "CSV"
3. Upload your CSV file (e.g., `asana_import.csv`)
4. Map fields (should be automatic)
5. Verify Priority field mapping
6. Import - subtasks will nest under parent tasks automatically

## Export Format

The converter always exports to **Asana-compatible format** with:

- **Native Asana subtasks** - True hierarchy, not just descriptions
- **Localized field names** - German "Priorität" or English "Priority"
- **UTF-8 BOM encoding** - Perfect Excel compatibility
- **Direct section assignment** - No custom field rules needed
- **8 optimized fields** - Essential fields including Parent task for subtasks

Example output structure:

```
Main Task: "Website redesign" (Priority: High, Due: 03/15/2025)
├─ Subtask: "Create wireframes" (Priority: High, Due: 03/05/2025, Tags: design)
├─ Subtask: "Implement responsive layout" (Priority: Medium, Due: 03/10/2025)
└─ Subtask: "SEO optimization" (Priority: Low, Tags: seo, testing)
```

## Data Processing

### Enhanced Metadata Preservation

The converter preserves rich metadata from the Backup Shortcut export:

- **Flagged tasks** → ⭐ Flagged (in description)
- **Reminders** → 🔔 Has Reminder (in description)
- **Locations** → 📍 Location: Office (in description)
- **URLs** → 🔗 URL: https://example.com (in description)
- **Subtasks** → Advanced Asana subtasks with individual due dates, priorities, and tags

### Advanced Subtasks Support

**Full Feature Parity:** Subtasks can have all the same features as main tasks:

- ✅ **Individual due dates** - Different from parent task
- ✅ **Individual priorities** - Independent priority levels (Low/Medium/High)
- ✅ **Individual tags** - Hashtags from titles + native tags combined
- ✅ **Individual URLs** - Separate links and resources
- ✅ **Enhanced metadata** - Flagged status, reminders, locations
- ✅ **Proper nesting** - Automatic parent-child relationships in Asana

Example subtask with full features:

```json
{
  "title": "Create wireframes #design #ux",
  "due_date": "2025-03-05T12:00:00Z",
  "prio": "Hoch",
  "tags": ["wireframe", "planning"],
  "flagged": "Ja",
  "url": "https://figma.com/wireframes"
}
```

This becomes a subtask in Asana with its own due date, priority, tags, and metadata - not just a simple checklist item.

### Tag Processing

**Important:** Asana CSV imports do not support direct tag mapping. Tags will be imported as "Tags (imported)" custom field.

Combined tag extraction:

- **Hashtags from titles**: `"Task #urgent #work"` → Tags: "urgent, work"
- **Native Apple tags**: `["project", "important"]` → Combined with hashtags
- **Format**: Comma-separated with spaces for readability
- **Deduplication**: Case-insensitive duplicate removal

**Manual mapping required:** After import, you can manually map "Tags (imported)" values to real Asana tags using Asana's multi-select features.

### Priority Mapping

| Apple (German) | Apple (English) | Asana (German) | Asana (English) |
| -------------- | --------------- | -------------- | --------------- |
| Ohne           | None            | (leer)         | (empty)         |
| Gering         | Low             | Niedrig        | Low             |
| Mittel         | Medium          | Mittel         | Medium          |
| Hoch           | High            | Hoch           | High            |

## Testing

Test with the included sample file:

```bash
# Test with sample data
python asana_convert.py -f examples/sample_bulk_reminders.json \
  -o test.csv --asana-language de -v

# Dry run test
python asana_convert.py -f examples/sample_bulk_reminders.json \
  --dry-run -v
```

## Troubleshooting

### Export Issues

- **Use only the Backup Shortcut** - Other export methods are outdated
- **Run shortcut on Mac** - Works best on macOS, large exports (500+ reminders) may take several minutes
- **Be patient with large exports** - Processing time increases with number of reminders and attachments
- **Duplicate reminders may occur** - The Backup Shortcut can sometimes create duplicate entries during export. This converter automatically removes them by default.

### Import Issues

- **Priority field not mapping** → Ensure global custom field exists
- **Subtasks not nesting** → Check parent task names match exactly
- **Encoding issues** → The tool automatically uses UTF-8 BOM for Excel compatibility
- **Missing sections** → Tasks import to project level, use sections within project
- **Tags not working** → Normal behavior! Tags become "Tags (imported)" custom field

### Duplicate Tasks

**Known Issue:** The "Backup Shortcut for Reminders" can sometimes create duplicate entries during the export process, especially with large reminder collections or when reminders exist in multiple lists.

The converter automatically removes these duplicates during conversion:

- **Common causes**: Large exports, cross-list references, shortcut processing quirks
- **Detection method**: Tasks with identical title, list, due date, and notes are considered duplicates
- **Default behavior**: Automatic deduplication (use `--no-deduplicate` to disable)
- **Verbose output**: Shows exactly which duplicates were removed

This saves you from manually cleaning up duplicates in Asana after import.

### Tags Import Limitation

**Known Asana limitation:** CSV imports cannot directly create Asana tags. This is expected behavior since 2018.

**What happens:**

- Tags column becomes "Tags (imported)" custom field
- Values like "urgent, work" are preserved as text
- This is NOT an error - it's how Asana works

**Workaround:**

1. Import CSV with "Tags (imported)" field
2. Use Asana's advanced search to filter by tag values
3. Multi-select tasks with same tag values
4. Manually add real Asana tags to selected tasks
5. Alternative: Create custom multi-select field instead of using tags

### Performance

- **Large files (1000+ reminders)** → Use `--dry-run` first to estimate
- **Memory usage** → Script handles 5000+ reminders efficiently
- **Processing time** → ~1-2 seconds per 100 reminders

## Backward Compatibility

The tool maintains compatibility with old single-reminder JSON files from apple-reminders-exporter for existing users.

**Recommendation:** Use the Backup Shortcut for Reminders for the best experience with bulk exports.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test with sample data
4. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Support

For issues:

1. Try with `--verbose` and `--dry-run` flags
2. Test with the sample file first
3. Check the Backup Shortcut export is valid JSON
4. Create a GitHub issue with anonymized sample data
