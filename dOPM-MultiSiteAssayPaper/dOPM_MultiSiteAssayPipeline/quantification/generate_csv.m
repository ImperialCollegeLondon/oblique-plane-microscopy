close all
clear all


output_dir   = '..\output';
% ALYtools_dir = 'C:\users\alexany\ALYtools';
ALYtools_dir = 'W:\software\ALYtools';
addpath(ALYtools_dir);
addpath_ALYtools;

% output_dir
% ='C:\tmp\Crick_accelerator_cross_partner_assay_EG_20240919\analysis\output';% hint at Yuriy local paths
% output_dir = 'U:\data\CALM\dOPM\working\IRB_accelerator_cross_partner_assay_ML_20241118\analysis\output';

conditions = {'DMSO','100 nm TPA +ve control','20 nm Binimetinib','60 nm Binimetinib','200 nm Binimetinib','3.5 um Binimetinib -ve control'};

rows={'B' 'C' 'D' 'E' 'F' 'G'};
cols={'5' '6' '7' '8'};
tiles={'0' '1' '2' '3' '4' '5' '6' '7' '8' '9'};

data = [];
data_spatial = [];
%
for R = 1:numel(rows)
    condition = conditions{R};
    for C = 1:numel(cols)
        well = [rows{R} cols{C}];
        for T = 1:numel(tiles)
            %
            fname = [rows{R} cols{C} '_tile_' tiles{T} '_fused_tp_0.csv'];
            fname_spatial = [rows{R} cols{C} '_tile_' tiles{T} '_fused_tp_0_spatial.csv'];
            %
            attributes = {well,condition,tiles{T}};             
            if isfile([output_dir filesep fname])
                [data_table,caption] = readcsv([output_dir filesep fname]);
                cur_data = [repmat(attributes,[size(data_table,1) 1]) data_table];
                data = [data; cur_data];                
            end
            if isfile([output_dir filesep fname_spatial])
                [data_table2,caption_spatial] = readcsv([output_dir filesep fname_spatial]);
                cur_data2 = [repmat(attributes,[size(data_table2,1) 1]) data_table2];
                data_spatial = [data_spatial; cur_data2];                                
            end            
            [R C T]
        end
    end
end

atrtibute_names = {'well' 'condition' 'tile'};

data = [[atrtibute_names caption]; data];
cell2csv([output_dir filesep 'main_quantification.csv'],data);

data_spatial = [[atrtibute_names caption_spatial]; data_spatial];
cell2csv([output_dir filesep 'spatial_quantification.csv'],data_spatial);

disp('done!');



% % tiles = [3 61];
% % time_points = [0 1];
% % 
% % u_well = {'B1','B2'};
% % u_biological_condition = {'negative','positive'};
% % %
% % tile_index_to_well_map = containers.Map(tiles,u_well);
% % tile_index_to_cond_map = containers.Map(tiles,u_biological_condition);
% % 
% % data = [];
% % data_spatial = [];
% % for tp = 1:length(time_points)
% %     for tile = 1:length(tiles)
% %         % tile_61_tp_0.csv
% %        fname = [output_dir filesep 'tile_' num2str(tiles(tile)) '_tp_' num2str(time_points(tp)) '.csv'];        
% %        fname_spatial = [output_dir filesep 'tile_' num2str(tiles(tile)) '_tp_' num2str(time_points(tp)) '_spatial.csv'];
% %        if isfile(fname_spatial) && isfile(fname)
% %            %
% %            cur_well = tile_index_to_well_map(tiles(tile));
% %            cur_cond = tile_index_to_cond_map(tiles(tile));
% %            % main quantification
% %            [data_table,caption] = readcsv(fname);
% %            cur_data = [repmat({cur_well},[size(data_table,1) 1]) ...
% %                        repmat({cur_cond},[size(data_table,1) 1]) ...
% %                        repmat({num2str(tiles(tile))},[size(data_table,1) 1]) ...
% %                        repmat({num2str(time_points(tp))},[size(data_table,1) 1]) data_table];
% %            data = [data; cur_data];
% %            % spatial quantification
% %            [data_table,caption_spatial] = readcsv(fname_spatial);
% %            cur_data = [repmat({cur_well},[size(data_table,1) 1]) ...
% %                        repmat({cur_cond},[size(data_table,1) 1]) ...
% %                        repmat({num2str(tiles(tile))},[size(data_table,1) 1]) ...
% %                        repmat({num2str(time_points(tp))},[size(data_table,1) 1]) data_table];
% %            data_spatial = [data_spatial; cur_data];           
% %        end
% %     end
% % end
% % 
% % data = [['well' 'condition' 'tile' 'time_point' caption]; data];
% % cell2csv([output_dir filesep 'main_quantification.csv'],data);
% % 
% % data_spatial = [['well' 'condition' 'tile' 'time_point' caption_spatial]; data_spatial];
% % cell2csv([output_dir filesep 'spatial_quantification.csv'],data_spatial);
% % 
% % disp('done!');

%-----------------------------------------------------------------------
function [data_table,caption] = readcsv(fname)
            data_table = readtable(fname);
            caption = data_table.Properties.VariableNames;
            data_table = table2cell(data_table);
end