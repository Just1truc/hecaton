FROM python:3.12-slim
RUN pip install torch --index-url https://download.pytorch.org/whl/cu121
RUN pip install hecaton==0.6.11
COPY handler.py /app/handler.py
CMD ["python", "/app/handler.py"]