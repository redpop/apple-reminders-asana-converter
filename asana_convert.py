#!/usr/bin/env python3
"""
Apple Reminders JSON to Asana CSV Converter
Konvertiert exportierte Apple Reminders JSON-Dateien in das Asana CSV-Import-Format
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
    """Kommandozeilen-Argumente parsen"""
    parser = argparse.ArgumentParser(
        description='Konvertiert Apple Reminders JSON-Dateien zu Asana CSV-Format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  # Einzelne Datei konvertieren
  python asana_convert.py -f reminder.json -o output.csv
  
  # Alle Dateien im Ordner (eine große CSV)
  python asana_convert.py -d json/ -o asana_import.csv
  
  # Alle Dateien im Ordner (separate CSVs)
  python asana_convert.py -d json/ --separate
  
  # Mit Assignee
  python asana_convert.py -d json/ -o asana_import.csv --assignee "john.doe@company.com"
  
  # Inkludiere auch erledigte Aufgaben (sonst nur offene)
  python asana_convert.py -d json/ -o all_tasks.csv --include-completed
        """
    )
    
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-f', '--file', type=str, help='Einzelne JSON-Datei zum Konvertieren')
    input_group.add_argument('-d', '--directory', type=str, help='Verzeichnis mit JSON-Dateien')
    
    parser.add_argument('-o', '--output', type=str, help='Ausgabe CSV-Datei (Standard: asana_import.csv)')
    parser.add_argument('--separate', action='store_true', help='Erstelle separate CSV-Dateien für jede JSON')
    parser.add_argument('--assignee', type=str, help='E-Mail-Adresse für Assignee (z.B. john.doe@company.com)')
    parser.add_argument('--include-completed', action='store_true', help='Inkludiere auch erledigte Aufgaben (Standard: nur offene Aufgaben)')
    parser.add_argument('--dry-run', action='store_true', help='Testlauf ohne Dateien zu schreiben')
    parser.add_argument('-v', '--verbose', action='store_true', help='Ausführliche Ausgabe')
    
    return parser.parse_args()


def format_date(date_string: str) -> str:
    """
    Konvertiert Apple-Datumsformat (ISO 8601) zu Asana-Format (MM/DD/YYYY)
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
            print(f"Warnung: Konnte Datum '{date_string}' nicht konvertieren: {e}")
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
    Extrahiert Tags aus dem Titel (z.B. #mac #development)
    Gibt bereinigten Titel und Liste der Tags zurück
    """
    tags = re.findall(r'#(\w+)', title)
    clean_title = re.sub(r'\s*#\w+', '', title).strip()
    return clean_title, tags


def format_section(list_name: str) -> str:
    """
    Formatiert den List-Namen als Section für Asana CSV
    Entfernt Doppelpunkt am Ende falls vorhanden (Asana fügt ihn automatisch hinzu)
    """
    if not list_name:
        return ''
    
    # Entferne Doppelpunkt am Ende falls vorhanden
    if list_name.endswith(':'):
        return list_name[:-1].strip()
    
    # Gib den Namen unverändert zurück
    return list_name


def convert_json_to_asana_row(json_data: Dict, default_assignee: Optional[str] = None) -> Dict:
    """
    Konvertiert eine einzelne JSON-Zeile zum Asana CSV-Format
    """
    # Tags aus Titel extrahieren
    title = json_data.get('Title', '')
    clean_title, tags = extract_tags_from_title(title)
    
    # Basis-Mapping - nur benötigte Felder
    assignee_email = default_assignee or ''
    
    # Versuche Namen aus E-Mail zu extrahieren, falls vorhanden
    assignee_name = ''
    if assignee_email:
        # Einfache Extraktion: vorname.nachname@domain.com -> Vorname Nachname
        local_part = assignee_email.split('@')[0]
        if '.' in local_part:
            name_parts = local_part.split('.')
            assignee_name = ' '.join(part.capitalize() for part in name_parts)
        else:
            assignee_name = local_part.capitalize()
    
    row = {
        'Name': clean_title or title,  # Falls keine Tags, Original-Titel verwenden
        'Description': json_data.get('Notes', ''),
        'Target Section': format_section(json_data.get('List', '')),  # Als Custom Field
        'Assignee': assignee_name,
        'Assignee Email': assignee_email,
        'Due Date': format_date(json_data.get('Due Date', '')),
        'Tags': ', '.join(tags) if tags else '',  # Tags aus Titel extrahiert
        'Priority': map_priority(json_data.get('Priority', ''))
    }
    
    # Tags sind jetzt im separaten Tags-Feld, nicht mehr in Description
    
    return row


def write_csv_file(filepath: str, rows: List[Dict], dry_run: bool = False):
    """Schreibt die CSV-Datei mit den konvertierten Daten"""
    if dry_run:
        print(f"[DRY RUN] Würde {len(rows)} Zeilen nach {filepath} schreiben")
        return
    
    # Asana CSV-Header - verwendet bestehende Asana-Feldnamen
    # "Priority" und "Target Section" sind globale benutzerdefinierte Felder
    # "Target Section" verhindert das Problem mit doppelten Sections beim Import
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
    Verarbeitet eine einzelne JSON-Datei
    Gibt True zurück wenn erfolgreich, False bei Fehler
    """
    try:
        if verbose:
            print(f"Verarbeite: {json_path}")
        
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Überspringe erledigte Aufgaben standardmäßig (außer wenn explizit gewünscht)
        if not include_completed and json_data.get('Is Completed', False):
            if verbose:
                print(f"  ⏭ Überspringe erledigte Aufgabe: {json_data.get('Title', 'Unbekannt')}")
            return True  # Als erfolgreich zählen, aber nicht verarbeiten
        
        # Konvertiere zu Asana-Format
        row = convert_json_to_asana_row(json_data, default_assignee)
        
        # Schreibe CSV
        write_csv_file(output_path, [row], dry_run)
        
        if not dry_run and verbose:
            print(f"  ✓ Erfolgreich konvertiert nach: {output_path}")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"  ✗ Fehler: Ungültiges JSON in {json_path}: {e}")
        return False
    except Exception as e:
        print(f"  ✗ Fehler beim Verarbeiten von {json_path}: {e}")
        return False


def process_directory(directory: str, output_path: Optional[str], separate: bool,
                     default_assignee: Optional[str] = None, include_completed: bool = False,
                     dry_run: bool = False, verbose: bool = False) -> Tuple[int, int, int]:
    """
    Verarbeitet alle JSON-Dateien in einem Verzeichnis
    Gibt Anzahl erfolgreicher, fehlgeschlagener und übersprungener Konvertierungen zurück
    """
    json_files = list(Path(directory).glob('*.json'))
    
    if not json_files:
        print(f"Keine JSON-Dateien in {directory} gefunden")
        return 0, 0, 0
    
    print(f"Gefunden: {len(json_files)} JSON-Dateien")
    
    success_count = 0
    error_count = 0
    skipped_count = 0
    all_rows = []
    
    for i, json_path in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}] {json_path.name}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Überspringe erledigte Aufgaben standardmäßig (außer wenn explizit gewünscht)
            if not include_completed and json_data.get('Is Completed', False):
                print(f"  ⏭ Überspringe erledigte Aufgabe: {json_data.get('Title', 'Unbekannt')}")
                skipped_count += 1
                continue
            
            row = convert_json_to_asana_row(json_data, default_assignee)
            
            if separate:
                # Separate CSV für jede Datei
                csv_name = json_path.stem + '_asana.csv'
                csv_path = json_path.parent / csv_name
                write_csv_file(str(csv_path), [row], dry_run)
                if verbose and not dry_run:
                    print(f"  ✓ Geschrieben nach: {csv_path}")
            else:
                # Sammle alle Zeilen für eine große CSV
                all_rows.append(row)
            
            success_count += 1
            
        except json.JSONDecodeError as e:
            print(f"  ✗ Ungültiges JSON: {e}")
            error_count += 1
        except Exception as e:
            print(f"  ✗ Fehler: {e}")
            error_count += 1
    
    # Wenn nicht separate, schreibe alle Zeilen in eine Datei
    if not separate and all_rows:
        output_file = output_path or 'asana_import.csv'
        write_csv_file(output_file, all_rows, dry_run)
        if not dry_run:
            print(f"\n✓ Alle {len(all_rows)} Aufgaben nach {output_file} geschrieben")
            print("\n💡 IMPORTANT NOTE:")
            print("   The CSV uses 'Target Section' as a custom field.")
            print("   Create a rule in Asana:")
            print("   'When Target Section = X, then move task to Section X'")
            print("   This prevents duplicate sections during import.")
    
    return success_count, error_count, skipped_count


def main():
    """Hauptfunktion"""
    global args
    args = parse_arguments()
    
    print("Apple Reminders → Asana CSV Konverter")
    print("=" * 40)
    
    if args.dry_run:
        print("[DRY RUN MODUS - Keine Dateien werden geschrieben]")
        print()
    
    if args.file:
        # Einzelne Datei verarbeiten
        output_path = args.output or 'asana_import.csv'
        success = process_single_file(
            args.file, output_path, args.assignee, 
            args.include_completed, args.dry_run, args.verbose
        )
        
        if success:
            print(f"\n✓ Konvertierung erfolgreich!")
            if not args.dry_run:
                print(f"CSV-Datei erstellt: {output_path}")
                print("\n💡 IMPORTANT NOTE:")
                print("   The CSV uses 'Target Section' as a custom field.")
                print("   Create a rule in Asana:")
                print("   'When Target Section = X, then move task to Section X'")
                print("   This prevents duplicate sections during import.")
        else:
            print("\n✗ Konvertierung fehlgeschlagen!")
            sys.exit(1)
            
    else:
        # Verzeichnis verarbeiten
        success, errors, skipped = process_directory(
            args.directory, args.output, args.separate,
            args.assignee, args.include_completed, args.dry_run, args.verbose
        )
        
        print("\n" + "=" * 40)
        print(f"Zusammenfassung:")
        print(f"  ✓ Erfolgreich: {success} Dateien")
        print(f"  ✗ Fehler: {errors} Dateien")
        if skipped > 0:
            print(f"  ⏭ Übersprungen: {skipped} erledigte Aufgaben (nutze --include-completed um alle zu konvertieren)")
        
        if success == 0:
            sys.exit(1)


if __name__ == "__main__":
    main()