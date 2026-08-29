"""Celery tasks for training."""
import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import UUID

from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from gto.config import get_settings
from gto.db.models import TrainingRun, ModelCheckpoint, ExploitabilityLog, TrainingStatus

settings = get_settings()

engine = create_async_engine(settings.DATABASE_URL, pool_pre_ping=True)
async_session_maker = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncSession:
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_training_task(self, run_id: str):
    """Run solver training in background."""
    run_uuid = UUID(run_id)

    async def _run():
        async with async_session_maker() as session:
            # Get training run
            result = await session.execute(select(TrainingRun).where(TrainingRun.id == run_uuid))
            run = result.scalar_one_or_none()
            if not run:
                return

            # Get checkpoint
            result = await session.execute(select(ModelCheckpoint).where(ModelCheckpoint.id == run.checkpoint_id))
            checkpoint = result.scalar_one_or_none()
            if not checkpoint:
                run.status = TrainingStatus.FAILED
                run.error_message = "Checkpoint not found"
                await session.commit()
                return

            run.status = TrainingStatus.RUNNING
            await session.commit()

            # Build command
            solutions_dir = Path(settings.SOLUTIONS_DIR)
            model_path = solutions_dir / checkpoint.file_path.split("/")[-1]

            cmd = [
                sys.executable, "-m", "gto.cli",
                "solve-full100" if checkpoint.model_type.value == "full100" else "solve-pushfold",
                "--model", str(model_path),
                "--iterations", str(run.target_iterations),
                "--save-every", "10000",
                "--report-every", "5000",
            ]

            if checkpoint.model_type.value == "pushfold":
                depth = checkpoint.config.get("depth_bb", 15)
                cmd = [
                    sys.executable, "-m", "gto.cli", "solve-pushfold",
                    "--depths", str(depth),
                    "--iterations", str(run.target_iterations),
                    "--save-every", "10000",
                    "--report-every", "5000",
                ]

            # Run solver with periodic exploitability logging
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd="/home/tuanlinh/poker",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )

            start_time = time.time()
            completed = 0

            async for line in process.stdout:
                line = line.decode().strip()
                if "iter" in line and "it/s" in line:
                    try:
                        parts = line.split("|")
                        iter_part = parts[0].strip()
                        completed = int(iter_part.split()[1])
                        it_per_sec = float(parts[1].strip().split()[0].replace(",", ""))

                        run.completed_iterations = completed
                        run.iterations_per_second = it_per_sec
                        await session.commit()

                        # Log exploitability every 5000 iterations
                        if completed % 5000 == 0 and completed > 0:
                            # Run exploitability check (simplified)
                            log = ExploitabilityLog(
                                checkpoint_id=checkpoint.id,
                                training_run_id=run.id,
                                iteration=completed,
                                exploitability_bb=0.0,  # TODO: actual measurement
                                br0_bb=0.0,
                                br1_bb=0.0,
                                trials=25,
                                boards_per_trial=10,
                            )
                            session.add(log)
                            await session.commit()
                    except Exception:
                        pass

            await process.wait()

            if process.returncode == 0:
                run.status = TrainingStatus.COMPLETED
                run.completed_at = time.time()
                run.completed_iterations = run.target_iterations
            else:
                run.status = TrainingStatus.FAILED
                run.error_message = f"Solver exited with code {process.returncode}"

            run.completed_at = time.time()
            await session.commit()

    asyncio.run(_run())


@shared_task
def measure_exploitability(checkpoint_id: str, iteration: int):
    """Measure and log exploitability for a checkpoint."""
    async def _measure():
        async with async_session_maker() as session:
            result = await session.execute(select(ModelCheckpoint).where(ModelCheckpoint.id == UUID(checkpoint_id)))
            checkpoint = result.scalar_one_or_none()
            if not checkpoint:
                return

            # TODO: Actually measure exploitability using solver
            # This is a placeholder
            log = ExploitabilityLog(
                checkpoint_id=checkpoint.id,
                iteration=iteration,
                exploitability_bb=0.0,
                br0_bb=0.0,
                br1_bb=0.0,
                trials=25,
                boards_per_trial=10,
            )
            session.add(log)
            await session.commit()

    asyncio.run(_measure())