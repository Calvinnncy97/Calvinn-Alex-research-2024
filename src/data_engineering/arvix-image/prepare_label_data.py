import os
all_imgs = os.listdir("/home/alextay96/Desktop/workspace/Calvinn-Alex-research-2024/src/data_engineering/arvix-image/figures")
all_urls = [f"http://localhost:8888/{x}" for x in all_imgs]
with open("img_to_label.txt", "w") as f:
    f.write("\n".join(all_urls))