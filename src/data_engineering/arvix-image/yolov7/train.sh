# python train_aux.py --workers 16 --device 0 --batch-size 16 --data custom/data.yaml --img 640 640 --cfg cfg/training/yolov7-w6.yaml --weights '/home/alextay96/Desktop/workspace/Calvinn-Alex-research-2024/src/data_engineering/arvix-image/yolov7-w6.pt' --name yolov7 --hyp data/hyp.scratch.p6.yaml



python train_aux.py --workers 4 --device 0 --batch-size 48 --data custom_dataset/data.yaml --img 640 640 --cfg cfg/training/yolov7-w6.yaml  --hyp data/hyp.scratch.p6.yaml --weights 'yolov7-w6.pt' --name yolov7