# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import time


http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency in seconds',
    ['method', 'endpoint', 'status'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0)
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'HTTP requests currently being processed',
    ['method', 'endpoint']
)

llm_requests_total = Counter(
    'llm_requests_total',
    'Total LLM API requests',
    ['model', 'status']
)

llm_request_duration_seconds = Histogram(
    'llm_request_duration_seconds',
    'LLM API request latency in seconds',
    ['model', 'status'],
    buckets=(0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0, 60.0)
)

resume_generation_total = Counter(
    'resume_generation_total',
    'Total resume generations',
    ['status']
)

resume_generation_failures = Counter(
    'resume_generation_failures_total',
    'Total number of resume generation failures',
    ['error_type']
)

resume_generation_duration_seconds = Histogram(
    'resume_generation_duration_seconds',
    'Resume generation duration in seconds',
    ['stage'],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0, 300.0]
)

resume_generation_in_progress = Gauge(
    'resume_generation_in_progress',
    'Number of resume generations currently in progress'
)

pdf_generation_attempts = Counter(
    'pdf_generation_attempts_total',
    'Total PDF generation attempts',
    ['result']
)

pdf_size_bytes = Histogram(
    'pdf_size_bytes',
    'PDF file size in bytes',
    buckets=[10000, 50000, 100000, 250000, 500000, 1000000, 2500000]
)

s3_upload_duration_seconds = Histogram(
    's3_upload_duration_seconds',
    'S3 upload duration in seconds',
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

s3_upload_failures = Counter(
    's3_upload_failures_total',
    'Total S3 upload failures',
    ['error_type']
)

ai_enhancement_duration_seconds = Histogram(
    'ai_enhancement_duration_seconds',
    'AI enhancement duration in seconds',
    ['section'],
    buckets=[0.5, 1.0, 2.5, 5.0, 10.0, 30.0]
)

ai_enhancement_failures = Counter(
    'ai_enhancement_failures_total',
    'Total AI enhancement failures',
    ['section']
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        method = request.method
        endpoint = self._get_endpoint_name(request)
        
        if endpoint == "/metrics":
            return await call_next(request)
        
        http_requests_in_progress.labels(method=method, endpoint=endpoint).inc()
        start_time = time.time()
        
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        
        except Exception as e:
            status = 500
            raise
        
        finally:
            duration = time.time() - start_time
            
            http_requests_total.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).inc()
            
            http_request_duration_seconds.labels(
                method=method,
                endpoint=endpoint,
                status=status
            ).observe(duration)
            
            http_requests_in_progress.labels(method=method, endpoint=endpoint).dec()
    
    def _get_endpoint_name(self, request: Request) -> str:
        path = request.url.path
        
        import re
        path = re.sub(
            r'/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}',
            '/{uuid}',
            path,
            flags=re.IGNORECASE
        )
        
        path = re.sub(r'/\d+', '/{id}', path)
        
        return path


def metrics_endpoint() -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


class ResumeGenerationMetrics:
    """Helper class for tracking resume generation metrics."""
    
    def __init__(self, resume_id: str):
        """
        Initialize metrics tracker for a resume generation session.
        
        Args:
            resume_id: Resume ID being processed
        """
        self.resume_id = resume_id
        self.start_time = time.time()
        self.stage_times = {}
        
        # Increment in-progress counter
        resume_generation_in_progress.inc()
    
    def track_stage(self, stage: str):
        """
        Context manager to track duration of a specific stage.
        
        Args:
            stage: Stage name (validation, ai_enhancement, html_render, etc.)
        """
        class StageTracker:
            def __init__(self, metrics_obj, stage_name):
                self.metrics = metrics_obj
                self.stage = stage_name
                self.stage_start = None
            
            def __enter__(self):
                self.stage_start = time.time()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                stage_duration = time.time() - self.stage_start
                self.metrics.stage_times[self.stage] = stage_duration
                resume_generation_duration_seconds.labels(stage=self.stage).observe(stage_duration)
        
        return StageTracker(self, stage)
    
    def record_success(self):
        """Record successful resume generation."""
        total_duration = time.time() - self.start_time
        resume_generation_duration_seconds.labels(stage='total').observe(total_duration)
        resume_generation_total.labels(status='complete').inc()
        resume_generation_in_progress.dec()
    
    def record_failure(self, error_type: str, error_message: str):
        """
        Record failed resume generation.
        
        Args:
            error_type: Error type (validation_error, pdf_error, etc.)
            error_message: Error message
        """
        total_duration = time.time() - self.start_time
        resume_generation_duration_seconds.labels(stage='total').observe(total_duration)
        resume_generation_failures.labels(error_type=error_type).inc()
        resume_generation_total.labels(status='error').inc()
        resume_generation_in_progress.dec()
    
    def record_pdf_attempt(self, success: bool, retry: bool = False):
        """
        Record PDF generation attempt.
        
        Args:
            success: Whether attempt was successful
            retry: Whether this was a retry attempt
        """
        if success:
            pdf_generation_attempts.labels(result='success').inc()
        elif retry:
            pdf_generation_attempts.labels(result='retry').inc()
        else:
            pdf_generation_attempts.labels(result='failure').inc()
    
    def record_pdf_size(self, size_bytes: int):
        """Record PDF file size."""
        pdf_size_bytes.observe(size_bytes)
    
    def record_s3_upload(self, duration: float, success: bool, error_type: str = None):
        """
        Record S3 upload metrics.
        
        Args:
            duration: Upload duration in seconds
            success: Whether upload was successful
            error_type: Error type if failed
        """
        s3_upload_duration_seconds.observe(duration)
        if not success and error_type:
            s3_upload_failures.labels(error_type=error_type).inc()
    
    def record_ai_enhancement(self, section: str, duration: float, success: bool):
        """
        Record AI enhancement metrics.
        
        Args:
            section: Section name (summary, experience, etc.)
            duration: Enhancement duration in seconds
            success: Whether enhancement was successful
        """
        ai_enhancement_duration_seconds.labels(section=section).observe(duration)
        if not success:
            ai_enhancement_failures.labels(section=section).inc()


def get_metrics_tracker(resume_id: str) -> ResumeGenerationMetrics:
    """
    Get metrics tracker for a resume generation session.
    
    Args:
        resume_id: Resume ID
        
    Returns:
        ResumeGenerationMetrics instance
    """
    return ResumeGenerationMetrics(resume_id)
