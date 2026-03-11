%% 配置
template_lay = 'A0.lay';
str2replace = {'A0.cas.gz', 'A0.dat.gz','default.xml'};    % 模板里原来的
output_folder = 'D:\Output\';

% 映射表：基础名 → {新数据文件列表}
% 只需要写 "A1"，程序自动生成 "A1.lay"
maps = {
    'A1', {'A1.cas.gz', 'A1.dat.gz','A1.xml'};
};

%% 执行
template = fileread(template_lay);
if ~exist(output_folder, 'dir'), mkdir(output_folder); end

for i = 1:size(maps, 1)
    base_name = maps{i, 1};           % 如 "A1"
    new_files = maps{i, 2};           % 如 {"A1.cas.gz", "A1.dat.gz"}
    
    % 替换
    content = template;
    for j = 1:length(str2replace)
        content = strrep(content, str2replace{j}, new_files{j});
    end
    
    % 自动生成 A1.lay
    fid = fopen(fullfile(output_folder, [base_name '.lay']), 'w');
    fwrite(fid, content);
    fclose(fid);
    
    fprintf('已生成: %s.lay\n', base_name);
end
