%% add paths for dependencies
clc
Rpath = 'C:\Users\CRICKOPMuser\Documents\GitHub';
paths =  {'\bf-tools','\PSF_MATLAB'};
addPaths(Rpath,paths);

%% settings 
% save outputs 
savedata = 0;
% debug
skipcode = 0; 

%% Expected contents of workspace per volume
% 
%   Name                   Size                Bytes  Class     Attributes
% 
%   FWHM                 296x4                  9472  double              
%   Ipaths                 1x4                  1418  cell                
%   analysis_folder        1x4                     8  char                
%   beadstats              1x1                   624  struct              
%   filepatterns           1x4                   648  cell                
%   i                      1x1                     8  double              
%   ii                     1x1                     8  double              
%   locArray             309x3                  7416  double              
%   locArrayKept           1x296                2368  double              
%   name                   1x152                 304  char                
%   settings               1x1                  4370  struct              
%   views                  1x296            15493824  cell  

ddrive = 'D:\bead_test\temp';

%% data
savepath = [ddrive '\results\'];

Ipaths = {
          [ddrive '\dOPM_0_5umz_steps_acquisition_17_5_prism_100nm_beads_6mmLS\results'],...
          [ddrive '\dOPM_0_5umz_steps_acquisition_22_5_prism_100nm_beads_6mmLS\results'],...
         };

filepatterns = {'decon_fused_tp_0_ch_0.mat',...
                'fused_fused_tp_0_ch_0.mat',...
                'view_fused_tp_0_vs_0.mat',...
                'view_fused_tp_0_vs_1.mat'...
                };

analysis_folder = 'temp';

volume_info = '100 nm beads from entire volume';

experiment = {
              '17.5 degree prism, 6mm diameter Light-sheet',...
              '22.5 degree prism, 6mm diameter Light-sheet',...
             };
    
conditions = {'deconvolved',...
             'fused',...
             'view 1',...
             'view 2',...
             };
         
metrics = {'FWHM_x',...
           'FWHM_y',...
           'FWHM_z',...
           'FWHM_zs',...
             };     
         
limits = {[0,1],...
          [0,1],...
          [0,3],...
          [0,6],...
           };         

limits_stats = {[0,.35],...
                [0,.35],...
                [0,1],...
                [0,4],...
                };        
%% check data 
off = 0;
if off == 1
else
    for i=1:numel(Ipaths)
        disp('checking data')
        disp(Ipaths{i})
        for ii=1:numel(filepatterns)
            name = fullfile(Ipaths{i},analysis_folder,filepatterns{ii});
            disp(name)
            load(name)
            disp('Contents of workspace after loading file:')
            if isempty(whos)
                disp('check data: aborted script - check file paths and patterns');
                return
            end
            whos
        end
    end
disp('all data found, running batch')
end

%% save path

if savedata == 1
   
    if settings.savedata == 1

        if ~exist(savepath, 'dir')
            mkdir(savepath)   
        end

    end

end
        
%% distance 
% options 1,2,3,4 for bead resolution as fn of x,y,z,radial 
%relative to volume centre
distance = 3; %  choose 1,2,3,4
%% CODE RUNS HERE

for i=1:numel(Ipaths)
   for ii=1:numel(filepatterns)
        %% outputs
        Ipath = fullfile(Ipaths{i},analysis_folder,filepatterns{ii});
        [filepath,name,ext] = fileparts(Ipath);

        % read volumes & inspect
        tic
        load(Ipath)
        whos
        disp('results loaded');
        toc
        
        %% get bead locations in pixels

        beads = locArray(locArrayKept,:);

        %% get volume dimensions and locations relative to centre of volume

        beads_origin = beads - settings.stackinfo{1}.imageDimensions/2;

        %% find the radial distance from the origin being on axis and zero refocus

        beads_refocus = vecnorm(beads_origin,2,2);

        %% find scaled radial distance from the origin being on axis and zero refocus
        if     distance == 1
            method = 'distance from origin along x';
            scaled_refocus = beads_origin(:,1)*settings.calibration;
        elseif distance == 2
            method = 'distance from origin along y';
            scaled_refocus = beads_origin(:,2)*settings.calibration;
        elseif distance == 3
            method = 'distance from origin along z';
            scaled_refocus = beads_origin(:,3)*settings.calibration;
        elseif distance == 4
            method = 'distance from origin radial';
            scaled_refocus = beads_refocus*settings.calibration;
        else
            disp('abort')
            return
        end
        %% scatter plot between scaled refocus and FWHM
        
        if ii == 1
            h1 = figure(i);
            set(h1,'WindowStyle','docked');
            clf
            sgtitle({volume_info,[experiment{i} ','],method});
        end
        
        subplot(4,4,1+4*(ii-1));
        plot(scaled_refocus,FWHM(:,1),'.');
        ylim(limits{1})
        xlabel('microns')
        title({conditions{ii},metrics{1}})
        subplot(4,4,2+4*(ii-1));
        plot(scaled_refocus,FWHM(:,2),'.');
        xlabel('microns')
        ylim(limits{2})
        title({conditions{ii},metrics{2}})
        subplot(4,4,3+4*(ii-1));
        plot(scaled_refocus,FWHM(:,3),'.');
        xlabel('microns')
        ylim(limits{3})
        title({conditions{ii},metrics{3}})
        subplot(4,4,4+4*(ii-1));
        plot(scaled_refocus,FWHM(:,4),'.');
        xlabel('microns')
        ylim(limits{4})
        title({conditions{ii},metrics{4}})
        
   end
   if savedata == 1
       saveas(h1,fullfile(savepath,[experiment{i} ' bead FWHM values as function of refocus.png']))
   end
end



%% do histograms

for i=1:numel(Ipaths)
   for ii=1:numel(filepatterns)
        %% outputs
        Ipath = fullfile(Ipaths{i},analysis_folder,filepatterns{ii});
        [filepath,name,ext] = fileparts(Ipath);
        % read volumes & inspect
        tic
        load(Ipath)
        whos
        disp('results loaded');
        toc   
        if ii == 1
            h2 = figure(i+6);
            set(h2,'WindowStyle','docked');
            clf
            sgtitle({volume_info,experiment{i}});
        end

        subplot(4,4,1+4*(ii-1));
        histogram(FWHM(:,1),100)
        xlim(limits{1})
        title({conditions{ii},metrics{1}})
        subplot(4,4,2+4*(ii-1));
        histogram(FWHM(:,2),100)
        xlim(limits{2})
        title({conditions{ii},metrics{2}})
        subplot(4,4,3+4*(ii-1));
        histogram(FWHM(:,3),100)
        xlim(limits{3})
        title({conditions{ii},metrics{3}})
        subplot(4,4,4+4*(ii-1));
        histogram(FWHM(:,4),100)
        xlim(limits{4})
        title({conditions{ii},metrics{4}})
        
   end
   if savedata == 1
       saveas(h2,fullfile(savepath,[experiment{i} ' histograms of bead FWHM values.png']))
   end
end

%% do summary statistics
FWHM_x=[];
FWHM_y=[];
FWHM_z=[];
FWHM_zs=[];
k=1;
for i=1:numel(filepatterns)
   for ii=1:numel(Ipaths)

       Ipath = fullfile(Ipaths{ii},analysis_folder,filepatterns{i});
       [filepath,name,ext] = fileparts(Ipath);

       % read volumes & inspect
       tic
       load(Ipath);
       disp('results loaded');
       toc
       
       stds = mad(FWHM,1) ; % median std
       
       FWHM_x(k) = beadstats.median(1);
       FWHM_y(k) = beadstats.median(2);
       FWHM_z(k) = beadstats.median(3);
       FWHM_zs(k) = beadstats.median(4);

       std_FWHM_x(k) = stds(1);
       std_FWHM_y(k) = stds(2);
       std_FWHM_z(k) = stds(3);
       std_FWHM_zs(k) = stds(4);
       
       k=k+1;
       
   end
end

stats = struct;
%%
stats.experimental_setup = {'17.5 degree prism, 3mm diameter light-sheet';...
              '17.5 degree prism, 6mm diameter light-sheet';...
              '17.5 degree prism, 9mm diameter light-sheet';...
              '22.5 degree prism, 3mm diameter light-sheet';...
              '22.5 degree prism, 6mm diameter light-sheet';...
              '22.5 degree prism, 9mm diameter light-sheet';...
              '17.5 degree prism, 3mm diameter light-sheet';...
              '17.5 degree prism, 6mm diameter light-sheet';...
              '17.5 degree prism, 9mm diameter light-sheet';...
              '22.5 degree prism, 3mm diameter light-sheet';...
              '22.5 degree prism, 6mm diameter light-sheet';...
              '22.5 degree prism, 9mm diameter light-sheet';...
              '17.5 degree prism, 3mm diameter light-sheet';...
              '17.5 degree prism, 6mm diameter light-sheet';...
              '17.5 degree prism, 9mm diameter light-sheet';...
              '22.5 degree prism, 3mm diameter light-sheet';...
              '22.5 degree prism, 6mm diameter light-sheet';...
              '22.5 degree prism, 9mm diameter light-sheet';...
              '17.5 degree prism, 3mm diameter light-sheet';...
              '17.5 degree prism, 6mm diameter light-sheet';...
              '17.5 degree prism, 9mm diameter light-sheet';...
              '22.5 degree prism, 3mm diameter light-sheet';...
              '22.5 degree prism, 6mm diameter light-sheet';...
              '22.5 degree prism, 9mm diameter light-sheet'...
};
          
stats.processing_type = {'deconvolved';...
                   'deconvolved';...
                   'deconvolved';...      
                   'deconvolved';...     
                   'deconvolved';...      
                   'deconvolved';...                        
                   'fused';...  
                   'fused';...  
                   'fused';...  
                   'fused';...  
                   'fused';...  
                   'fused';...  
                   'view 1';...  
                   'view 1';...  
                   'view 1';...  
                   'view 1';...  
                   'view 1';...  
                   'view 1';... 
                   'view 2';...  
                   'view 2';...  
                   'view 2';...  
                   'view 2';...  
                   'view 2';...  
                   'view 2'};
               
stats.median_FWHM_x = FWHM_x';
stats.median_FWHM_y = FWHM_y';
stats.median_FWHM_z = FWHM_z';
stats.median_FWHM_zs = FWHM_zs';
               
stats.std_FWHM_x = std_FWHM_x';
stats.std_FWHM_y = std_FWHM_y';
stats.std_FWHM_z = std_FWHM_z';
stats.std_FWHM_zs = std_FWHM_zs';
              
% number of measurements actually collected
N = numel(FWHM_x);

% truncate metadata to match
stats.experimental_setup = stats.experimental_setup(1:N);
stats.processing_type    = stats.processing_type(1:N);

% now convert to table
T = struct2table(stats);

disp(T);

if savedata == 1
    saveas(h3,fullfile(savepath,' histograms of median bead FWHM values.png'))
    filename = [savepath 'FwhmValues.xls'];
    delete(filename)
    writetable(T,filename)
end
%% plot summary statistics

h3 = figure(13);
set(h3,'WindowStyle','docked');
clf

labels = cat(2,T.experimental_setup,T.processing_type);
categories={};

for i=1:size(labels,1)
    strng = [labels{i,1} ' ' labels{i,2}];
    strng = regexprep(strng,' degree prism,',' P,');
    strng = regexprep(strng,'deconvolved','D');
    strng = regexprep(strng,' diameter light-sheet','LS');
    strng = regexprep(strng,'mm','');
    strng = regexprep(strng,'view ','v');
    strng = regexprep(strng,'fused','f');
    categories{i} = strng;
end

c = categorical(categories);
c = reordercats(c,categories);

subplot(4,1,1)
bar(c,T.median_FWHM_x)
title('FWHM_{x} lab frame')
grid on
grid minor
ylim(limits_stats{1})

subplot(4,1,2)
bar(c,T.median_FWHM_y)
title('FWHM_{y} lab frame')
grid on
grid minor
ylim(limits_stats{2})

subplot(4,1,3)
bar(c,T.median_FWHM_z)
title('FWHM_{z} lab frame')
grid on
grid minor
ylim(limits_stats{3})

subplot(4,1,4)
bar(c,T.median_FWHM_zs)
title('FWHM_{zs} lab frame')
grid on
grid minor
ylim(limits_stats{4})

sgtitle({[volume_info ','], ' bar plot of median bead FWHM values.png'})

if savedata == 1
    saveas(h3,fullfile(savepath,' histograms of median bead FWHM values.png'))
end
%% plot all the points

categories={'17.5 P, 3mm LS','17.5 P, 6mm LS','17.5 P, 9mm LS','22.5 P, 3mm LS','22.5 P, 6mm LS','22.5 P, 9mm LS'};

c = categorical(categories);
c = reordercats(c,categories);

h4 = figure(14);
set(h4,'WindowStyle','docked');
clf

hold on

subplot(4,1,1)
bar(c,reshape(T.median_FWHM_x,[6,4]))
title('FWHM_{x} lab frame')
grid on
grid minor
ylim(limits_stats{1})
Lgnd = legend('deconvolved','fused','view 1','view 2');
Lgnd.Position(1) = 0.85;
Lgnd.Position(2) = 0.85;
subplot(4,1,2)
bar(c,reshape(T.median_FWHM_y,[6,4]))
title('FWHM_{y} lab frame')
grid on
grid minor
ylim(limits_stats{2})
% legend('deconvolved','fused','view 1','view 2')
subplot(4,1,3)
bar(c,reshape(T.median_FWHM_z,[6,4]))
title('FWHM_{z} lab frame')
grid on
grid minor
ylim(limits_stats{3})
% legend('deconvolved','fused','view 1','view 2')
subplot(4,1,4)
bar(c,reshape(T.median_FWHM_zs,[6,4]))
title('FWHM_{zs} lab frame')
grid on
grid minor
ylim(limits_stats{4})
% legend('deconvolved','fused','view 1','view 2')

sgtitle({[volume_info ','], ' bar plot of median bead FWHM values.png'})

if savedata == 1
    saveas(h4,fullfile(savepath,' histograms of median bead FWHM values grouped by experimental setup.png'))
end
%% plot all the points

categories={'deconvolved','fused','view 1','view 2'};

c = categorical(categories);
c = reordercats(c,categories);

h5 = figure(15);
set(h5,'WindowStyle','docked');
clf

hold on

subplot(4,1,1)
bar(c,reshape(T.median_FWHM_x,[6,4])')
title('FWHM_{x} lab frame')
grid on
grid minor
ylim(limits_stats{1})
Lgnd = legend('17.5 P, 3mm LS','17.5 P, 6mm LS','17.5 P, 9mm LS','22.5 P, 3mm LS','22.5 P, 6mm LS','22.5 P, 9mm LS');
Lgnd.Position(1) = 0.85;
Lgnd.Position(2) = 0.85;
subplot(4,1,2)
bar(c,reshape(T.median_FWHM_y,[6,4])')
title('FWHM_{y} lab frame')
grid on
grid minor
ylim(limits_stats{2})
% legend('deconvolved','fused','view 1','view 2')
subplot(4,1,3)
bar(c,reshape(T.median_FWHM_z,[6,4])')
title('FWHM_{z} lab frame')
grid on
grid minor
ylim(limits_stats{3})
% legend('deconvolved','fused','view 1','view 2')
subplot(4,1,4)
bar(c,reshape(T.median_FWHM_zs,[6,4])')
title('FWHM_{zs} lab frame')
grid on
grid minor
ylim(limits_stats{4})

sgtitle({[volume_info ','], ' bar plot of median bead FWHM values.png'})

if savedata == 1
    saveas(h5,fullfile(savepath,' histograms of median bead FWHM values grouped by processing method.png'))
end
%% functions go here

function addPaths(Rpath,paths)
% function adds dependencies
  for i = 1:numel(paths)
        addpath(genpath([Rpath,paths{i}]));
  end
end

function rmPaths(Rpath,paths)
% function removes dependencies
  for i = 1:numel(paths)
        rmpath(genpath([Rpath,paths{i}]));
  end
end