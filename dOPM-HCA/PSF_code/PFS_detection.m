%% add paths for dependencies
clc
Rpath = 'C:\Users\User\Documents\GitHub';
paths =  {'\bf-tools','\PSF_MATLAB'};
addPaths(Rpath,paths);

%% settings 
settings.int = 0.001; % interpolates for FWHM
settings.backpercentile = 5; %for estimating background in each subvol
settings.LPrange =[-5,5];  % range to display line profile plots
settings.offset_raw = 120; % camera offset 120
settings.threshold = 200;   % threshold for DoG binarising 30
settings.Expected_diamter = 4; % PSF diameter in pixels 224 nm / 74
settings.box_size = [30,80]; % only takes even number, expects sparse beads with box only contianing one bead dims for box in x/y/z
settings.plot =1; % display settings
rnge =[0,300]; % display settings
settings.bead_location_choice = 3;%only use method 3
choices = ["Centroid of Binary","Centroid of signal","Max of signal"];
choice = choices(settings.bead_location_choice);
% save outputs 
settings.savedata = 1;
% debug
skipcode = 0; 

%% data

savepathsubfolder = '\temp\';

Ipaths = {'D:\bead_test\'};
     
filepatterns = {'fusion_fused_tp_0_ch_0.tif'};

%% check data 
for i=1%2:3%4:5%:numel(Ipaths)
    disp('checking data')
    disp(Ipaths{i})
    for ii=1:numel(filepatterns)
        stackinfo = bfinfo(fullfile(Ipaths{i},filepatterns{ii}));
        disp(stackinfo{1}.name)
        if isempty(stackinfo)
            disp('check data: aborted script - check file paths and patterns');
            return
        end
    end
end
disp('all data found, running batch')

%% CODE RUNS HERE

for i=1%:numel(Ipaths)
   for ii=1%:numel(filepatterns)
        %% outputs
        Ipath = fullfile(Ipaths{i},filepatterns{ii});
        [filepath,name,ext] = fileparts(Ipath);
        setings.filepath = filepath;
        settings.name = name;
        settings.savepath = [filepath savepathsubfolder];

        if settings.savedata == 1

            if ~exist(settings.savepath, 'dir')
                mkdir(settings.savepath)   
            end

        end

        % read volumes & inspect
        tic

        stack = bfread(Ipath, 1, 'TimePoint', 1, 'Channel', 1);
        settings.stackinfo = bfinfo(Ipath);
        if range(stackinfo{1}.pixelDimensions)<1e-6
            settings.calibration = settings.stackinfo{1}.pixelDimensions(1);
        else
            disp('aborted, voxels not isotropic')
            settings.calibration = NaN;
            return
        end

        disp('stack loaded');
        toc

        %% show MIP to check data
        fignum = 1;
        showMIPStack(stack,fignum)
        
        if skipcode ~= 1

            %% get DoG & inspect for single volume
            fignum = 2;
            tic
            DoG = GetDoG(stack,settings,rnge,fignum);
            disp('DoG completed')
            toc
            %% find centroid of each binarised bead region
            tic
            [locArray,DoGBW]=GetBeadLocations(DoG,stack,settings,choice);
            disp('bead locations found from DoG')
            toc
            %% fly through subvolumes and get line profiles - both return same locArrayKept
            tic
            [FWHM,locArrayKept,views] = BeadFlyThruLineProfiles(stack,locArray,fignum,settings);
            disp('fly through beads completed')
            toc
            %% plot histogram and summary stats
            beadstats = getstats(FWHM);

            disp(Ipath);
            disp(beadstats);

            if settings.plot ==1 
                PlotFWHM(FWHM)
            end

            if settings.savedata == 1
                 save([settings.savepath name '.mat'],...
                 'FWHM','settings','views','locArray','locArrayKept','beadstats',...
                 '-mat');
            end
        else
            disp('SKIPPING CODE')
        end
   end
end

%% FUNCTIONS GO HERE
function beadstats  = getstats(FWHM)
    beadstats = struct;
    beadstats.mean = mean(FWHM,'omitnan');
    beadstats.median = median(FWHM,'omitnan');
    beadstats.std = std(FWHM,0,'omitnan');
end

function PlotFWHM(FWHM)

    fignum = 4;
    figure(fignum)
    subplot(2,2,1)
    histogram(FWHM(:,1))
    title('X FWHM distribution')
    xlabel('FWHM_{x} \mum')
    subplot(2,2,2)
    histogram(FWHM(:,2))
    title('Y FWHM distribution')
    xlabel('FWHM_{y} \mum')
    subplot(2,2,3)
    histogram(FWHM(:,3))
    title('Z FWHM distribution')
    xlabel('FWHM_{z} \mum')
    subplot(2,2,4)
    histogram(FWHM(:,4))
    title('Zs FWHM distribution')
    xlabel('FWHM_{z} \mum')

end

function stack = GetStack(Ipath,dtype)
    %dtypes = {'uint16'};
    stack = ReadTiffStack(Ipath,dtype);

end

function [Stack] = ReadTiffStack(StackName,dtype)

   %loadVolumeStack loads the volume as a tiff stack. 

    InfoImage=imfinfo(StackName);
    mImage=InfoImage(1).Width;
    nImage=InfoImage(1).Height;
    NumberImages = regexp(InfoImage(1).ImageDescription, 'images=(\d*)','tokens');
    NumberImages = str2double(NumberImages{1});
    Stack=zeros(nImage,mImage,NumberImages,'single');
    fp = fopen(StackName, 'rb');
    fseek(fp, InfoImage(1).StripOffsets, 'bof');
    
    for i = 1:NumberImages   
        if dtype == 'uint16'
            Stack(:,:,i) = fread(fp, [InfoImage(1).Width InfoImage(1).Height], 'uint16', 0, 'ieee-be')';
        elseif dtype == 'single'
            Stack(:,:,i) = fread(fp, [InfoImage(1).Width InfoImage(1).Height], 'single', 0, 'ieee-be')';
        else
            disp('incorrect dtype')
        end
    end
    
    fclose(fp);


end

function [DoG] = GetDoG(data,settings,rnge,fignum)
    % DoG setup
    % data is 3D volume
    % sigma A is width scale of bandpass edge
    % sigma B is width scale of bandpass edge
    % Expected_diamter - pixel size and estimated PSF FWHM assume bead subdiffraction
    
    sigma_A = (1/(1+sqrt(2)))*settings.Expected_diamter;
    sigma_B = sqrt(2)*sigma_A;
    
    tic
    A = imgaussfilt3(data,sigma_A);
    B = imgaussfilt3(data,sigma_B);
    toc

    DoG = A - B;
    
    if settings.plot == 1

        h=figure(fignum);
        clf
%             clc
        colormap gray

        set(h,'WindowStyle','docked');

        subplot(3,3,1)

        imagesc(squeeze(max(A,[],3)),rnge);
        title('X - HIGH PASS')
        subplot(3,3,2)

        imagesc(squeeze(max(A,[],2))',rnge);
        title('Y - HIGH PASS')
        subplot(3,3,3)

        imagesc(squeeze(max(A,[],1))',rnge);
        title('Z - HIGH PASS')

        subplot(3,3,4)
        title('X - LOW PASS')
        imagesc(squeeze(max(B,[],3)),rnge);
        subplot(3,3,5)

        imagesc(squeeze(max(B,[],2))',rnge);
        title('Y - LOW PASS')
        subplot(3,3,6)

        imagesc(squeeze(max(B,[],1))',rnge);
        title('Z - LOW PASS')

        subplot(3,3,7)

        imagesc(squeeze(max(DoG,[],3)),rnge);
        title('X - DoG')
        subplot(3,3,8)

        imagesc(squeeze(max(DoG,[],2))',rnge);
        title('Y - DoG')
        subplot(3,3,9)

        imagesc(squeeze(max(DoG,[],1))',rnge);
        title('Z - DoG')

    end

end

function [locArray,DoGBW]=GetBeadLocations(DoG,data,settings,choice)
    tic 
    T = settings.threshold;
    DoGBW = imbinarize(DoG,T);
    
    if choice == "Centroid of Binary"
        locations = regionprops3(DoGBW,"Centroid");
        locArray = table2array(locations);
    elseif choice == "Centroid of signal"
        locations = regionprops3(DoGBW,data,"Centroid");
        locArray = table2array(locations);
    elseif choice == "Max of signal"
        locations_improved = regionprops3(DoGBW,data,"Centroid","VoxelValues","VoxelList");
        num = size(locations_improved,1);
        locArray = zeros(num,3);
        for i=1:num
            [~,I]=max(locations_improved.VoxelValues{i});
            locArray(i,:)= locations_improved.VoxelList{i}(I,:);
        end
    else
        disp('choice not valid')
    end
    
    disp(['found: ' num2str(size(locArray,1)) ' beads'])
    toc

end

function [FWHM,locArrayKept,views] = BeadFlyThruLineProfiles(data,locArray,fignum,settings)
% goes through a volume pulls out bead data at each DoG locArray value in
% subvolume given by box_size, gets bead FWHM values in x,y,z

    h=figure(fignum);
    set(h,'WindowStyle','docked');
    
    locArrayKept = [];
    dims =  size(data);
    box_size = floor(settings.box_size)/2; 
    beads = size(locArray,1);
    views={beads,4};
    FWHM = zeros(beads,4); % FWHM in x,y,z
    
    tic;
    mb=0;
    for i=1:beads
        disp(['bead: ' num2str(i)]);
            if min(floor(locArray(i,1:2))-box_size(1))<1 ||...
               min(floor(locArray(i,3))-box_size(2))<1 ||...
               min([dims(2),dims(1)]-(floor(locArray(i,1:2))+box_size(1)))<0 ||...
               min([dims(3)]-(floor(locArray(i,3))+box_size(2)))<0
                disp("bead at edge: skip");      
            else  
                dists = locArray;
                dists(i,:) = [];
                dists = dists - locArray(i,:); 
                for ii =1:size(dists,1)
                    dists(ii,:) = cat(2,(abs(dists(ii,1)) < (box_size(1)+1)),(abs(dists(ii,2)) < (box_size(1)+1)),abs(dists(ii,3)) < (box_size(2)+1));
                end
                
                if max(sum(dists,2))==3
                    disp('multiple beads');
                    mb=mb+1;
                    disp(num2str(mb));
                else   
                    Y = floor(locArray(i,2))-box_size(1):floor(locArray(i,2))+box_size(1);
                    X = floor(locArray(i,1))-box_size(1):floor(locArray(i,1))+box_size(1);
                    Z = floor(locArray(i,3))-box_size(2):floor(locArray(i,3))+box_size(2);

                    sub = data(Y,X,Z);
        %           back = min(sub,[],'all')
                    back = prctile(sub,settings.backpercentile,'all');
                    sub = sub - back;

                    CoM = [box_size(1)+1,box_size(1)+1,box_size(2)+1];

                    [x,y]=getLineProfiles(sub,CoM,settings,1);
                    FWHM(i,1)=getFWHM(x,y,settings.int);
                    Y = [x;y'];

                    [x,y]=getLineProfiles(sub,CoM,settings,2);
                    FWHM(i,2)=getFWHM(x,y,settings.int);
                    X = [x;y];

                    [x,y]=getLineProfiles(sub,CoM,settings,3);
                    FWHM(i,3)=getFWHM(x,y,settings.int);
                    Z = [x;y'];

                    [x,y]=getSectioningProfiles(sub,settings);
                    FWHM(i,4)=getFWHM(x,y,settings.int);
                    Zs = [x;y'];        

                    if settings.plot == 1
                        subplot(2,4,1);
                        %hold on
                        plot(Y(1,:),Y(2,:));
                        title('Y')
                        xlabel('distance \mum')
                        ylabel('intensity')
                        xlim(settings.LPrange);
                        ylim([0,inf])
                        subplot(2,4,2);
                        %hold on
                        plot(X(1,:),X(2,:));
                        title('X')
                        xlabel('distance \mum')
                        ylabel('intensity')
                        xlim(settings.LPrange);
                        ylim([0,inf])
                        subplot(2,4,3);
                        %hold on
                        plot(Z(1,:),Z(2,:));
                        title('Z')
                        xlabel('distance \mum')
                        ylabel('intensity')
                        xlim(settings.LPrange);
                        ylim([0,inf])
                        subplot(2,4,4);
                        %hold on
                        plot(Zs(1,:),Zs(2,:));
                        title('Zs')
                        xlabel('distance \mum')
                        ylabel('intensity')
                        xlim(settings.LPrange);
                        ylim([0,inf])
                    
                    end

                    % naming is specific to dOPM data....
                    YX = squeeze(sub(:,:,CoM(3)));%YX
                    YZ = squeeze(sub(:,CoM(2),:));%YZ
                    XZ = squeeze(sub(CoM(1),:,:));%XZ

                    if settings.plot == 1
                        subplot(2,4,5);
                        imagesc(YX);
                        title('XY')
                        subplot(2,4,6);
                        imagesc(YZ);
                        title('ZY')
                        subplot(2,4,7);
                        imagesc(XZ);
                        title('ZX')
                        drawnow
                    end

                    views{i} = {YX,YZ,XZ,X,Y,Z,Zs};
                    locArrayKept=[locArrayKept,i];
                end
            
        end
        

    end
    
    FWHM = FWHM(locArrayKept,:);
    views = views(locArrayKept);
    
    disp('recovered line FWHM & line profiles') 
    toc;
    

end

function [x,y]=getSectioningProfiles(data,settings)

    y = squeeze(sum(data,[1,2])); 
    lngth = size(data,3);
    [~,idx]=max(y);
    x = (settings.calibration)*(1-idx:lngth-idx);
       
end

function [x,y]=getLineProfiles(data,CoM,settings,dim)

    lngth = size(data,dim);
    
    if dim == 1 % y-axis
        [~,idx]=max(data(:,CoM(2),CoM(3)));
        x = (settings.calibration)*(1-idx:lngth-idx);
        y = squeeze(data(:,CoM(2),CoM(3)));
    end
    
    if dim == 2 % x-axis
        [~,idx]=max(data(CoM(1),:,CoM(3)));
        x = (settings.calibration)*(1-idx:lngth-idx);
        y = squeeze(data(CoM(1),:,CoM(3)));
    end
  
    if dim == 3 % z-axis
        [~,idx]=max(data(CoM(1),CoM(2),:));
        x = (settings.calibration)*(1-idx:lngth-idx);
        y = squeeze(data(CoM(1),CoM(2),:));
    end
        
end

function [FWHM]=getFWHM(x,y,int)
    intx = x(1):int:x(end);
    inty = interp1(x,y,intx,'spline');%linear spline
    maxy = max(y);
    A = find(inty>0.5*maxy,1,'first'); %(not valid, if A is the first or B is the last)
    B = find(inty>0.5*maxy,1,'last'); %change the condition
    
    if isempty(A)||isempty(B)
            FWHM = nan;
            disp("FWHM is not correct");        
    else    
        if B == numel(inty)||A == 1
            FWHM = nan;
            disp("FWHM is not correct");
        else
            FWHM = abs(intx(B)-intx(A));
        end
    end
end

function showMIP(data,fignum)

    % transposing specific to data from dOPM btw...
    h=figure(fignum);
    clf(h);
    subplot(1,3,1)
    title('XY')
    imagesc(squeeze(max(data,[],2))); %XY
    subplot(1,3,2)
    title('ZY')
    imagesc(squeeze(max(data,[],2))'); %ZY
    subplot(1,3,3)
    title('ZX')
    imagesc(squeeze(max(data,[],2))'); %ZX
    
end

function views = showOrth(data,fignum,CoM)

    % transposing specific to data from dOPM btw...
    h=figure(fignum);
    clf(h);
    
    % naming is specific to dOPM data....
    YX = squeeze(data(:,:,CoM(3)));%YX
    YZ = squeeze(data(:,CoM(2),:));%YZ
    XZ = squeeze(data(CoM(1),:,:));%XZ

    subplot(2,2,1);
    imagesc(YX);
    title('XY')
    subplot(2,2,2);
    imagesc(YZ);
    title('ZY')
    subplot(2,2,3);
    imagesc(XZ);
    title('ZX')
    drawnow
    
    views = {YX,YZ,XZ};
    
end

function showOrthLineProfiles(Y,X,Z,Zs,fignum,LPrange)
% transposing specific to data from dOPM btw...
    
    h=figure(fignum);
    clf(h);
    
    subplot(2,2,1);
    hold on
    plot(Y(1,:),Y(2,:));
    title('Y')
    xlabel('distance \mum')
    ylabel('intensity')
    xlim(LPrange);
    subplot(2,2,2);
    hold on
    plot(X(1,:),X(2,:));
    title('X')
    xlabel('distance \mum')
    ylabel('intensity')
    xlim(LPrange);
    subplot(2,2,3);
    hold on
    plot(Z(1,:),Z(2,:));
    title('Z')
    xlabel('distance \mum')
    ylabel('intensity')
    xlim(LPrange);
    subplot(2,2,4);
    hold on
    plot(Zs(1,:),Zs(2,:));
    title('Zs')
    xlabel('distance \mum')
    ylabel('intensity')
    xlim(LPrange);
    drawnow
    
end

function showMIPStack(stack,fignum)

    h=figure(fignum);
    clf
%     clc
    colormap gray
    set(h,'WindowStyle','docked');

    nVol=size(stack,4);

    for i = 1:nVol

        subplot(nVol,3,1+(i-1)*3)
        imagesc(squeeze(max(stack(:,:,:),[],3)));
        title('X')
        subplot(nVol,3,2+(i-1)*3)
        imagesc(squeeze(max(stack(:,:,:),[],2))');
        title('Y')
        subplot(nVol,3,3+(i-1)*3)
        imagesc(squeeze(max(stack(:,:,:),[],1))');
        title('Z')

    end

end


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