FROM python:3.12-slim
RUN pip install hecaton==0.6.10
COPY handler.py /app/handler.py
CMD ["python", "/app/handler.py"]