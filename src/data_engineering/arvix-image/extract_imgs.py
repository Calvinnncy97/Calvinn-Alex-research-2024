
from loguru import logger
from tqdm import tqdm
from pdf2image import convert_from_path
import os
import glob
def convert_pdf_to_images(pdf_path, output_folder):
    # Ensure output directory exists
    try:
        arvix_filename = pdf_path.split('/')[-1].replace("pdf", "").replace(".", "")
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        # Convert PDF to a list of images
        images = convert_from_path(pdf_path)
        
        # Save each image as a separate file
        for i, image in tqdm(enumerate(images), total=len(images)):
            image_path = os.path.join(output_folder, f'{arvix_filename}_page_{i+1}.png')
            image.save(image_path, 'PNG')
    except Exception as e1:
        logger.warning(f"E1 : {e1}")

if __name__ == "__main__":
    output_folder = "/home/alextay96/Desktop/workspace/Calvinn-Alex-research-2024/src/data_engineering/arvix-image/figures"
    src_dir = "/home/alextay96/Desktop/workspace/Calvinn-Alex-research-2024/src/data_engineering/arvix-image/pdf"
    for pdf_path in tqdm(glob.glob(f"{src_dir}/*.pdf")):
        convert_pdf_to_images(pdf_path, output_folder)
