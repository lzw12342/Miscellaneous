// =====================================================
// Fiji 终极版 - 使用正确的Results保存方法
// =====================================================

// 路径格式是 "盘符:\\目录1\\目录2\\...\\目录n\\"
inputFolder = "H:\\01-KEDL\\KEDL\\图片处理 气泡\\1-G10-Q161-W10-A28-V7-n1_C001H001S0001\\新建文件夹\\";
outputFolder = "H:\\01-KEDL\\KEDL\\图片处理 气泡\\1-G10-Q161-W10-A28-V7-n1_C001H001S0001\\冲击深度处理后\\";

// ========== 循环外的预处理 ==========
if (!File.exists(outputFolder)) {
    File.makeDirectory(outputFolder);
}

files = getFileList(inputFolder);
jpgFiles = newArray(0);
for (i = 0; i < files.length; i++) {
    if (endsWith(files[i], ".jpg") || endsWith(files[i], ".JPG")) {
        jpgFiles = Array.concat(jpgFiles, files[i]);
    }
}

if (jpgFiles.length == 0) {
    exit("❌ 错误: 输入文件夹中没有JPG文件!");
}

print("=== 发现 " + jpgFiles.length + " 个JPG文件 ===");

// 初始化
setBatchMode(true);
run("Clear Results");
if (isOpen("Summary")) {
    selectWindow("Summary");
    run("Close");
}

// 【关键】设置测量参数，确保Results包含详细数据
run("Set Measurements...", "area mean min centroid perimeter shape feret's display redirect=None decimal=3");

// ========== 主循环 ==========
for (i = 0; i < jpgFiles.length; i++) {
    fileName = jpgFiles[i];
    fullPath = inputFolder + fileName;
    
    while (nImages > 0) {
        selectImage(nImages);
        close();
    }
    roiManager("reset");
    run("Clear Results");
    
    open(fullPath);
    if (nImages == 0) continue;
    
    // 处理流程
    // run("Sharpen");
    // setAutoThreshold("Default dark no-reset");
    // run("Threshold...");
    // setThreshold(82, 255);
    // setOption("BlackBackground", true);
    // run("Convert to Mask");
    // run("Close-");
    // run("Fill Holes");
    // run("Watershed");
    // setTool("polygon");
    // makePolygon(533,630,818,526,1159,541,1024,769,846,950,596,844);
        
    // 【关键】不带 clear，display 参数让Results保留数据
    run("Analyze Particles...", "size=10-500 circularity=0.00-1.00 show=Nothing exclude display include summarize");
    
    baseName = replace(replace(fileName, ".jpg", ""), ".JPG", "");
    
    // 保存Results（需要暂时退出批处理模式）
    if (nResults > 0) {
        setBatchMode("exit and display");  // 退出并显示Results
        saveAs("Results", outputFolder + baseName + "_results.csv");
        setBatchMode(true);  // 恢复批处理
    }
    
    // 保存图像
    if (nImages > 0) {
        saveAs("Jpeg", outputFolder + baseName + "_processed.jpg");
        close();
    }
    
    // 进度
    if ((i+1) % 50 == 0) {
        print("已处理: " + (i+1) + "/" + jpgFiles.length);
    }
}

// ========== 收尾 ==========
setBatchMode(false);

// 保存Summary
if (isOpen("Summary")) {
    selectWindow("Summary");
    saveAs("Results", outputFolder + "ALL_IMAGES_summary.csv");
    print("✓ Summary已保存");
}

while (nImages > 0) {
    selectImage(nImages);
    close();
}

