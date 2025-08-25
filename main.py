"""
Talent Search Chatbot - Refactored Version

This is the main entry point for the application.
The application has been refactored into multiple modules:
- config.py: Configuration and logging setup
- database.py: Database connection
- intent_parser.py: Intent parsing functionality
- sql_builder.py: SQL query building
- query_executor.py: Query execution and data merging
- scoring.py: Employee scoring algorithms
- formatter.py: Result formatting
- logger_helper.py: Logging helpers
- ui.py: UI application
- main.py: Main application entry point (in src directory)

To run the application, execute this file.
"""

if __name__ == "__main__":
    # Import and run the main application from the src directory
    import tkinter as tk
    from src.config import logger
    from src.ui import App
    
    root = tk.Tk()
    app = App(root)
    logger.info("Talent Search Chatbot started.")
    root.mainloop()