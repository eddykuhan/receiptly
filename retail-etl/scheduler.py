"""
APScheduler daemon for running ETL pipeline nightly.
"""
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime
import signal
import sys

from etl_manager import ETLManager
from config.settings import SCHEDULE_HOUR, SCHEDULE_MINUTE, LOG_FILE

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ETLScheduler:
    """Scheduler for automated ETL execution."""
    
    def __init__(self):
        """Initialize the scheduler."""
        self.scheduler = BlockingScheduler()
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown handlers."""
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)
    
    def shutdown(self, signum, frame):
        """Gracefully shutdown the scheduler."""
        logger.info("Received shutdown signal. Stopping scheduler...")
        self.scheduler.shutdown()
        sys.exit(0)
    
    def run_etl_job(self):
        """Execute the ETL pipeline."""
        logger.info(f"Scheduled ETL job triggered at {datetime.now()}")
        try:
            manager = ETLManager()
            manager.run_pipeline()
        except Exception as e:
            logger.error(f"Error in scheduled ETL job: {e}", exc_info=True)
    
    def start(self):
        """Start the scheduler."""
        # Add the ETL job with cron trigger (runs daily at configured time)
        self.scheduler.add_job(
            self.run_etl_job,
            trigger=CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE),
            id='etl_job',
            name='Retail Price ETL Pipeline',
            replace_existing=True
        )
        
        logger.info(f"ETL Scheduler started. Job will run daily at {SCHEDULE_HOUR:02d}:{SCHEDULE_MINUTE:02d}")
        logger.info("Press Ctrl+C to exit")
        
        try:
            self.scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Scheduler stopped")


def main():
    """Main entry point."""
    scheduler = ETLScheduler()
    scheduler.start()


if __name__ == "__main__":
    main()
