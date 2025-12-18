#gmail: ljlzxxx2@gmail.com

import imaplib
import email
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
import getpass
import sys

class GmailEmailDeleter:
    def __init__(self, email_address, password):
        self.email_address = email_address
        self.password = password
        self.imap_server = "imap.gmail.com"
        self.mail = None
    
    def connect(self):
        """Connect to Gmail via IMAP"""

        try:
            print(f"Connecting to {self.imap_server}...")
            self.mail = imaplib.IMAP4_SSL(self.imap_server) # port 993
            self.mail.login(self.email_address, self.password)
            print("Successfully connected to Gmail!")
            return True
        
        except imaplib.IMAP4.error as e:

            print(f"Login failed: {e}")
            print("\nNote: You need to use an App Password for Gmail, not the regular password:")
            print("1. Go to Google Account settings: https://myaccount.google.com/security")
            print("2. Go to 2 step verification and find 'APP Password'")
            print("3. Use that 16-character App Password created instead of your regular password")
            return False
        
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def list_folders(self):
        """List all available folders/labels"""
        try:
            status, folders = self.mail.list()
            if status == 'OK':
                print("\nAvailable folders/labels:")
                for folder in folders:
                    folder_str = folder.decode()
                    # Extract just the folder name from the full response
                    # Format is usually: (flags) "delimiter" "folder_name"
                    parts = folder_str.split('"')
                    if len(parts) >= 3:
                        folder_name = parts[-2]
                        # Try to select the folder and get message count
                        # If Cannot select, only print folder name
                        try:
                            status, messages = self.mail.select(f'"{folder_name}"', readonly=True)
                            if status == 'OK':
                                count = int(messages[0])
                                print(f"  {folder_str} [{count} emails]")
                            else:
                                print(f"  {folder_str}")
                        except:
                            print(f"  {folder_str}")

                    else:
                        print(f"  {folder_str}")
        except Exception as e:
            print(f"Error listing folders: {e}")

    
    def delete_emails_by_date_range(self, start_date, end_date, folder="INBOX", dry_run=True):
        """
        Delete emails within a date range
        
        Args:
            start_date: datetime object for the start date (inclusive)
            end_date: datetime object for the end date (inclusive)
            folder: Email folder to search (default: "INBOX")
                   Common Gmail folders: "INBOX", "[Gmail]/Sent Mail", "[Gmail]/Trash", "[Gmail]/Spam"
            dry_run: If True, only shows what would be deleted without actually deleting
        """
        try:
            print(f"\nSelecting folder: {folder}")
            status, messages = self.mail.select(f'"{folder}"')
            
            if status != 'OK':
                print(f"Failed to select folder {folder}")
                print("Try using one of the folders listed above.")
                return
            
            total_emails = int(messages[0])
            print(f"Total emails in {folder}: {total_emails}")
            

            start_str = start_date.strftime("%d-%b-%Y")
            end_str = end_date.strftime("%d-%b-%Y")
            
            print(f"\nSearching for emails from {start_str} to {end_str}...")
            

            next_day = end_date + timedelta(days=1)
            next_day_str = next_day.strftime("%d-%b-%Y")
            

            search_criteria = f'(SINCE "{start_str}" BEFORE "{next_day_str}")'
            status, email_ids = self.mail.search(None, search_criteria)
            
            if status != 'OK':
                print("Search failed")
                return
            
            email_id_list = email_ids[0].split()
            
            if not email_id_list:
                print("No emails found in the specified date range.")
                return
            
            print(f"Found {len(email_id_list)} emails in date range")
            
            if dry_run:
                print("\n=== DRY RUN MODE ===")
                print("Showing first 10 emails that would be deleted:")
                
                for i, email_id in enumerate(email_id_list[:10]):
                    status, msg_data = self.mail.fetch(email_id, '(RFC822)')
                    if status == 'OK':
                        email_message = email.message_from_bytes(msg_data[0][1])
                        subject = email_message.get('Subject', 'No Subject')
                        from_addr = email_message.get('From', 'Unknown')
                        date = email_message.get('Date', 'Unknown')
                        print(f"\n{i+1}. From: {from_addr}")
                        print(f"   Subject: {subject}")
                        print(f"   Date: {date}")
                
                if len(email_id_list) > 10:
                    print(f"\n... and {len(email_id_list) - 10} more emails")
                
                print(f"\nTotal emails that would be deleted: {len(email_id_list)}")
                print("\nTo actually delete these emails, run with dry_run=False")
            else:
                print("\n=== DELETING EMAILS ===")
                print(f"This will move {len(email_id_list)} emails to Trash.")
                print("Note: In Gmail, emails in Trash are automatically deleted after 30 days.")
                confirm = input(f"Are you sure you want to delete {len(email_id_list)} emails? (yes/no): ")
                
                if confirm.lower() != 'yes':
                    print("Deletion cancelled.")
                    return
                
                deleted_count = 0
                
                for i, email_id in enumerate(email_id_list, 1):
                    self.mail.store(email_id, '+X-GM-LABELS', '\\Trash')
                    deleted_count += 1
                    
                    if i % 100 == 0:
                        print(f"Moved {i}/{len(email_id_list)} emails to Trash...")
                
                print(f"\n✓ Successfully moved {deleted_count} emails to Trash!")
                print("These emails will be permanently deleted from Trash after 30 days.")
        
        except Exception as e:
            print(f"Error during deletion: {e}")
            import traceback
            traceback.print_exc()
    
    def permanently_delete_from_trash(self, dry_run=True):
        """
        Permanently delete all emails from Trash
        WARNING: This cannot be undone!
        """
        try:
            trash_folder = "[Gmail]/Trash"
            print(f"\nSelecting folder: {trash_folder}")
            status, messages = self.mail.select(f'"{trash_folder}"')
            
            if status != 'OK':
                print(f"Failed to select {trash_folder}")
                return
            
            total_emails = int(messages[0])
            print(f"Total emails in Trash: {total_emails}")
            
            if total_emails == 0:
                print("Trash is empty.")
                return
            
            status, email_ids = self.mail.search(None, 'ALL')
            
            if status != 'OK':
                print("Search failed")
                return
            
            email_id_list = email_ids[0].split()
            
            if dry_run:
                print(f"\n=== DRY RUN MODE ===")
                print(f"Would permanently delete {len(email_id_list)} emails from Trash")
                print("\nTo actually delete these emails, run with dry_run=False")
            else:
                print("\n=== PERMANENTLY DELETING FROM TRASH ===")
                print("⚠️  WARNING: This action CANNOT be undone!")
                confirm = input(f"Are you ABSOLUTELY sure you want to permanently delete {len(email_id_list)} emails? (type 'DELETE' to confirm): ")
                
                if confirm != 'DELETE':
                    print("Deletion cancelled.")
                    return
                
                for i, email_id in enumerate(email_id_list, 1):
                    self.mail.store(email_id, '+FLAGS', '\\Deleted')
                    
                    if i % 100 == 0:
                        print(f"Deleted {i}/{len(email_id_list)} emails...")
                
                self.mail.expunge()
                print(f"\n✓ Permanently deleted {len(email_id_list)} emails from Trash!")
        
        except Exception as e:
            print(f"Error during permanent deletion: {e}")
            import traceback
            traceback.print_exc()
    
    def close(self):
        """Close the IMAP connection"""
        if self.mail:
            try:
                self.mail.close()
                self.mail.logout()
                print("\nDisconnected from Gmail")
            except:
                pass


def main():
    print("=" * 60)
    print("Gmail Bulk Email Deleter")
    print("=" * 60)
    
    email_address = input("\nEnter your Gmail address: ")
    password = getpass.getpass("Enter your App Password: ")
    
    deleter = GmailEmailDeleter(email_address, password)
    
    if not deleter.connect():
        return
    
    deleter.list_folders()
    
    print("\n" + "=" * 60)
    print("Enter the date range for emails to delete")
    print("=" * 60)
    
    try:
        start_date_str = input("Start date (YYYY-MM-DD): ")
        end_date_str = input("End date (YYYY-MM-DD): ")
        
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")
        
        if start_date > end_date:
            print("Error: Start date must be before end date")
            return
        
        print("\nCommon folders:")
        print("  INBOX - Main inbox")
        print("  [Gmail]/Sent Mail - Sent emails")
        print("  [Gmail]/Spam - Spam folder")
        print("  [Gmail]/Trash - Trash folder")
        
        folder = input("\nFolder to search (press Enter for INBOX): ").strip()
        if not folder:
            folder = "INBOX"
        
        print("\n" + "=" * 60)
        deleter.delete_emails_by_date_range(start_date, end_date, folder, dry_run=True)
        
        print("\n" + "=" * 60)
        proceed = input("\nDo you want to proceed with deletion? (yes/no): ")
        
        if proceed.lower() == 'yes':
            deleter.delete_emails_by_date_range(start_date, end_date, folder, dry_run=False)
            
            print("\n" + "=" * 60)
            empty_trash = input("\nDo you want to permanently delete emails from Trash now? (yes/no): ")
            
            if empty_trash.lower() == 'yes':
                deleter.permanently_delete_from_trash(dry_run=False)
        else:
            print("Deletion cancelled.")
    
    except ValueError as e:
        print(f"Invalid date format: {e}")
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user")
    finally:
        deleter.close()


if __name__ == "__main__":
    main()