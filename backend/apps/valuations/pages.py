"""Bounded PDF rasterisation for document suggestions and the evidence viewer."""
import io
import threading
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.common.http import IntakeError

PDF_LOCK = threading.Lock()  # PDFium is not thread safe.


def render_pdf(content, name, remaining):
    import pypdfium2 as pdfium
    try:
        with PDF_LOCK:
            pdf = pdfium.PdfDocument(content)
            try:
                if not 0 < len(pdf) <= remaining:
                    raise IntakeError(f'The PDF exceeds the remaining {remaining}-page allowance. Upload at most 10 pages in total.')
                pages = []
                for index in range(len(pdf)):
                    page = pdf[index]
                    width, height = page.get_size()
                    if min(width, height) <= 0:
                        raise IntakeError('This PDF has an invalid page size.')
                    bitmap = page.render(scale=min(2, 2200 / max(width, height)))
                    image = bitmap.to_pil()
                    output = io.BytesIO()
                    image.convert('RGB').save(output, format='JPEG', quality=90)
                    pages.append(SimpleUploadedFile(f'{name}-page-{index + 1}.jpg', output.getvalue(), content_type='image/jpeg'))
                    image.close()
                    bitmap.close()
                    page.close()
                return pages
            finally:
                pdf.close()
    except pdfium.PdfiumError:
        raise IntakeError('The PDF could not be opened. Use an unlocked PDF or photographs of the pages.') from None
