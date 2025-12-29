"""
Contact Data Deduplication Script
---------------------------------
Removes duplicate contacts from new data based on existing data.
Uses normalized phone numbers (Indonesian format starting with 0) as unique identifier.
"""

import json


def normalize_phone(phone: str) -> str:
    """
    Normalize phone number to Indonesian format starting with '0'.
    
    Examples:
        628123456789  -> 08123456789
        08123456789   -> 08123456789
        8123456789    -> 08123456789
        +628123456789 -> 08123456789
    """
    if not phone:
        return ""
    
    # Remove all non-digit characters
    digits = ''.join(c for c in phone if c.isdigit())
    
    # Convert 62xxx to 0xxx
    if digits.startswith('62') and len(digits) > 2:
        digits = '0' + digits[2:]
    # Add leading 0 if starts with 8
    elif digits.startswith('8'):
        digits = '0' + digits
    # Ensure starts with 0
    elif not digits.startswith('0') and len(digits) > 0:
        digits = '0' + digits
    
    return digits


def load_json(filepath: str) -> dict:
    """Load JSON file and return parsed data."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json(data: dict, filepath: str) -> None:
    """Save data to JSON file with indentation."""
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_existing_phones(contacts: list) -> set:
    """Extract normalized phone numbers from contact list."""
    phones = set()
    for contact in contacts:
        phone = contact.get('phone', '')
        normalized = normalize_phone(phone)
        if normalized:
            phones.add(normalized)
    return phones


def filter_new_contacts(new_contacts: list, existing_phones: set) -> list:
    """Filter out contacts whose phone numbers already exist."""
    unique_contacts = []
    seen_phones = set()
    
    for contact in new_contacts:
        phone = contact.get('phone', '')
        normalized = normalize_phone(phone)
        
        if not normalized:
            continue
        
        # Skip if phone exists in old data or already seen in new data
        if normalized in existing_phones or normalized in seen_phones:
            continue
        
        # Update contact with normalized phone
        cleaned_contact = {
            'name': contact.get('name', ''),
            'phone': normalized
        }
        
        # Include notes if present
        if 'notes' in contact and contact['notes']:
            cleaned_contact['notes'] = contact['notes']
        
        unique_contacts.append(cleaned_contact)
        seen_phones.add(normalized)
    
    return unique_contacts


def main():
    # File paths
    old_data_file = 'data.json'
    new_data_file = 'data_baru.json'
    output_file = 'data_baru_clean.json'
    
    print("[INFO] Contact Deduplication Script")
    print("=" * 50)
    
    # Load data
    print(f"[LOAD] Reading {old_data_file}...")
    old_data = load_json(old_data_file)
    old_contacts = old_data.get('contacts', [])
    print(f"       Found {len(old_contacts)} existing contacts")
    
    print(f"[LOAD] Reading {new_data_file}...")
    new_data = load_json(new_data_file)
    new_contacts = new_data.get('contacts', [])
    print(f"       Found {len(new_contacts)} new contacts")
    
    # Get existing phone numbers
    print("[PROCESS] Extracting existing phone numbers...")
    existing_phones = get_existing_phones(old_contacts)
    print(f"          {len(existing_phones)} unique existing phones")
    
    # Filter new contacts
    print("[PROCESS] Filtering duplicates...")
    unique_contacts = filter_new_contacts(new_contacts, existing_phones)
    
    # Calculate stats
    removed_count = len(new_contacts) - len(unique_contacts)
    
    # Save result
    output_data = {'contacts': unique_contacts}
    save_json(output_data, output_file)
    
    # Summary
    print("=" * 50)
    print("[DONE] Deduplication Complete")
    print(f"       Original new contacts: {len(new_contacts)}")
    print(f"       Duplicates removed:    {removed_count}")
    print(f"       Unique new contacts:   {len(unique_contacts)}")
    print(f"       Output saved to:       {output_file}")


if __name__ == '__main__':
    main()
