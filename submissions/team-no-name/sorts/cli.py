import argparse
import sys
import os
import logging
from sorts.database.connection import init_db, get_db
from sorts.services.seed_service import seed_database
from sorts.services.session_service import SessionService
from sorts.services.import_service import ImportService
from sorts.services.club_service import ClubService
from sorts.database import models as db_models

# Configure simple stdout logging for CLI
logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")
logger = logging.getLogger("sorts-cli")

def main():
    parser = argparse.ArgumentParser(
        description="Sortling V1 Command Line Interface. Manage university seeding, crawling, and matching."
    )
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # 1. Seed Command
    seed_parser = subparsers.add_parser("seed", help="Initialize and seed the database with standard data.")
    seed_parser.add_argument(
        "--file", 
        default="sorts/assets/data/mahindra_seed.json", 
        help="Path to the seed JSON file."
    )

    # 2. Import Command
    import_parser = subparsers.add_parser("import", help="Run crawler and trait inference pipeline on an ImportSource.")
    import_parser.add_argument("--source-id", type=int, required=True, help="ID of the ImportSource to crawl.")

    # 3. List Drafts Command
    list_drafts_parser = subparsers.add_parser("list-drafts", help="Lists draft changes for a crawled job.")
    list_drafts_parser.add_argument("--job-id", type=int, required=True, help="ImportJob ID.")

    # 4. Publish Command
    publish_parser = subparsers.add_parser("publish", help="Approve and promote draft clubs to live university clubs.")
    publish_parser.add_argument("--job-id", type=int, required=True, help="ImportJob ID.")

    # 5. Interactive Command
    interactive_parser = subparsers.add_parser("interactive", help="Start an interactive matching questionnaire session.")
    interactive_parser.add_argument(
        "--university-slug", 
        default="mahindra", 
        help="Slug of the university (default: mahindra)."
    )
    interactive_parser.add_argument(
        "--user-name", 
        default="cli_user", 
        help="Simulated user identification string."
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    # Initialize the database file and tables if missing
    init_db()

    with get_db() as db:
        if args.command == "seed":
            if not os.path.exists(args.file):
                print(f"Error: Seed file not found at '{args.file}'. Please check the path.", file=sys.stderr)
                sys.exit(1)
            seed_database(db, args.file)
            print("Database seeded successfully.")

        elif args.command == "import":
            import_svc = ImportService()
            print(f"Starting import for source ID {args.source_id}...")
            try:
                job_id = import_svc.trigger_import(db, args.source_id)
                print(f"Import completed. Job ID: {job_id}. Run 'list-drafts --job-id {job_id}' to review drafts.")
            except Exception as e:
                print(f"Import failed: {str(e)}", file=sys.stderr)
                sys.exit(1)

        elif args.command == "list-drafts":
            import_svc = ImportService()
            diff = import_svc.get_draft_diff(db, args.job_id)
            print(f"Draft differences for Job {args.job_id}:")
            print("=" * 60)
            
            # Print categorized results
            for status, list_dc in diff.items():
                print(f"{status.upper()} ({len(list_dc)}):")
                for d in list_dc:
                    print(f"  - {d.name} ({d.summary})")
                    traits_str = ", ".join(f"{t.trait.slug}:{t.weight:.1f}" for t in d.traits)
                    print(f"    Traits: {traits_str}")
                    print(f"    Links: Web={d.website or '-'}, Discord={d.discord or '-'}, Insta={d.instagram or '-'}")
                print("-" * 60)

        elif args.command == "publish":
            import_svc = ImportService()
            print(f"Publishing changes for Job {args.job_id}...")
            try:
                import_svc.publish_job(db, args.job_id)
                print("Changes published successfully. Live club directory updated.")
            except Exception as e:
                print(f"Publish failed: {str(e)}", file=sys.stderr)
                sys.exit(1)

        elif args.command == "interactive":
            # Start Adaptive questionnaire in the console
            univ = db.query(db_models.University).filter_by(slug=args.university_slug).first()
            if not univ:
                print(f"Error: University '{args.university_slug}' not found. Did you run 'seed'?", file=sys.stderr)
                sys.exit(1)

            session_svc = SessionService()
            session = session_svc.create_session(db, univ.id, args.user_name)
            session_id = session.id

            print("\n" + "=" * 60)
            print(f"   WELCOME TO SORTLING - {univ.name} GUIDE")
            print("=" * 60)
            print("Sortling: Hmm... Let's find where you belong. Answer these questions:")

            question_count = 0
            while True:
                # Refresh session inside transaction to avoid detached objects
                question_db = session_svc.get_next_question(db, session_id)
                if not question_db:
                    break

                question_count += 1
                print(f"\n[{question_count}] {question_db.text}")
                
                # Render options
                options = question_db.options
                for idx, opt in enumerate(options):
                    print(f"  {idx + 1}) {opt.text}")

                # Prompt user for input
                choice = -1
                while True:
                    try:
                        ans_str = input("\nYour answer (number): ").strip()
                        choice = int(ans_str) - 1
                        if 0 <= choice < len(options):
                            break
                        print(f"Please enter a number between 1 and {len(options)}.")
                    except ValueError:
                        print("Invalid input. Please enter a valid number.")

                selected_opt = options[choice]
                session_svc.submit_answer(db, session_id, question_db.id, selected_opt.id)

            print("\nSortling: I have a theory. Let me calculate...")
            recs = session_svc.generate_recommendations(db, session_id, limit=3)

            print("\n" + "=" * 60)
            print("   RECOMMENDED CLUBS")
            print("=" * 60)
            for r in recs:
                club = r.club
                print(f"\nRank {r.rank}: {club.name}")
                print(f"   Summary: {club.summary}")
                print(f"   Description: {club.description}")
                print(f"   Explanation: {r.explanation}")
                
                socials = []
                if club.website and club.website != "-":
                    socials.append(f"Web={club.website}")
                if club.discord and club.discord != "-":
                    socials.append(f"Discord={club.discord}")
                if club.instagram and club.instagram != "-":
                    socials.append(f"Insta={club.instagram}")
                links_str = ", ".join(socials) if socials else "None"
                print(f"   Links: {links_str}")
                print("-" * 60)
            
            # Simple prompt for feedback
            print("\nSortling: How did I do? Enter feedback rating (1-5, or press Enter to skip):")
            rating_str = input("Rating (1-5): ").strip()
            if rating_str.isdigit():
                rating = int(rating_str)
                if 1 <= rating <= 5:
                    comment = input("Additional comments (optional): ").strip()
                    # Log feedback for first recommendation
                    if recs:
                        fb = db_models.Feedback(
                            recommendation_id=recs[0].id,
                            rating=rating,
                            comments=comment if comment else None
                        )
                        db.add(fb)
                        db.commit()
                        print("Sortling: Thank you! Feedback registered.")

            print("\nSortling: Good luck on campus! Bye!\n")

if __name__ == "__main__":
    main()
