
function process_FOV_collar_modified()

rehash toolboxcache;

matlab_job_spec = getenv('matlab_job_spec');
if exist('matlab_job_spec','var') &&~ isempty(matlab_job_spec)
    sep='@';
    p = strsplit(matlab_job_spec,sep);
else
    disp('error - no job spec found');
    return;
end

%$job_spec$sep$data_dir$sep$output_dir$sep$ALYtools_dir$sep$channels$sep$extension
ji           = p{1};
tp           = p{2};
tile         = p{3};
data_dir     = p{4};
output_dir   = p{5};
ALYtools_dir = p{6};
channels     = p{7};
extension    = p{8};

try
    assert(isfolder(output_dir));
    assert(isfolder(data_dir));
    assert(isfolder(ALYtools_dir));
    %
    %tile_99_fused_tp_0_ch_1.tif    
    for c=1:length(channels)
     fname = [data_dir filesep 'tile_' tile '_fused_tp_' tp '_ch_' channels(c) extension];
        assert(isfile(fname)) 
    end
 catch
    disp('error - wrong I/O arrangement');
    return;
 end

addpath(ALYtools_dir);
addpath_ALYtools;   

ini_Bioformats();

% ch_0 488 laser, 530/43 filter -> Membrane
% ch_1 561 laser, 630/69 filter -> Sensor
% ch_2 640 laser, 694/44 filter -> Nucleus

[~,~,membrane] = bfopen_v([data_dir filesep 'tile_' tile '_fused_tp_' tp '_ch_' '0' extension]);
[~,~,sensor] = bfopen_v([data_dir filesep 'tile_' tile '_fused_tp_' tp '_ch_' '1' extension]);
[~,~,nucleus] = bfopen_v([data_dir filesep 'tile_' tile '_fused_tp_' tp '_ch_' '2' extension]);

membrane = single(squeeze(membrane(:,:,:,1,1)));
nucleus = single(squeeze(nucleus(:,:,:,1,1)));
sensor = single(squeeze(sensor(:,:,:,1,1)));
[sx,sy,sz] = size(sensor);

% needs something better, - findpeaks.
bckg_membrane = get_above_background_threshold(single(membrane),0)
bckg_nucleus = get_above_background_threshold(single(nucleus),0)
bckg_sensor = get_above_background_threshold(single(sensor),0)

membrane(0==membrane) = bckg_membrane;
nucleus(0==nucleus) = bckg_nucleus;
sensor(0==sensor) = bckg_sensor;

fov_token = ['tile_' tile '_tp_' tp]

tic

umppix = 0.68;
     
    %1 micron
    r = round(1./umppix);
    % 3.5 microns
    min_diameter = round(3.5/umppix);
    se_r = strel('sphere',round(r));
    
            u = nucleus; % segment nuclei here..    
            %u = log(u); %?
                      
            S1 = round(min_diameter/2.25);
            S2 = S1*2;
            S3 = S2*4;            
            a1 = 0.7;
            %
            z = three_scale_tophat(u,S1,S2,S3,a1);
            %
            %t = 0.024;
            t = 0.07;
            z = z > t;    
            %
            CLEARBORDER = true;
            %CLEARBORDER = false;
            min_sieve_out_size = min_diameter^3;
            dmap_smooth_length = 1.5*r;
            sgm_nuc = clean_and_watershed_nuclei(z,r,min_sieve_out_size,dmap_smooth_length,CLEARBORDER);
            
            z = sgm_nuc>0;            
            
            se = strel('sphere',round(fix(15/umppix))); % glue them together!           
            z = imdilate(z,se);
            z = imerode(z,se);
            
            z_lab = bwlabeln(z);
            s = regionprops3(z_lab,'Volume');
            x = s.Volume;
            index = find(x==max(x));
            in_blob = z_lab == index;
            sgm_nuc = sgm_nuc & in_blob;
            sgm_nuc = bwlabeln(sgm_nuc>0);                                                
            %           
            v = zeros(sx,sy,2,sz,1);
            v(:,:,1,:,1) = u; % 2
            v(:,:,2,:,1) = membrane; % 0            
            v(:,:,3,:,1) = sensor; % 1                        
            v(:,:,4,:,1) = sgm_nuc;
            if ispc 
                try
                    icy_imshow(uint16(v),fov_token);
                catch
                end 
            end
                        
disp(['nuclei segmentation - done, processing time [min] ' num2str(toc/60)]);

    % shell // "try collars"
    n_nuc = max(sgm_nuc(:));
    sgm_collars = zeros(size(sgm_nuc));
    mask = sgm_collars; % used to remove intersecting areas
    %
    se_r_collar = strel('sphere',2*round(r));
    dilated_nuc = imdilate(sgm_nuc,se_r_collar); % same as **
    parfor k=1:n_nuc
        k
        z = sgm_nuc==k;
        % collar
        z = imdilate(z,se_r_collar); % same as **
        z = imdilate(z,se_r_collar) &~ z;
        z = z &~ dilated_nuc;
        %
        sgm_collars = sgm_collars + k*(z==1);
        mask = mask + (z==1);
    end
    sgm_collars = sgm_collars.*(mask==1);

    n_nuc = max(sgm_nuc(:))
    n_collars = max(sgm_collars(:))
        
    if n_nuc > n_collars
        disp('reducing #nuc, to keep nuclear to collar correspondence..');
        sgm_nuc(sgm_nuc > n_collars) = 0;
    end
    
    n_nuc = max(sgm_nuc(:))
    n_collars = max(sgm_collars(:))
        
    assert(n_collars==n_nuc);

disp(['collars - done, processing time [min] ' num2str(toc/60)]);
%     

%     
    membrane_corr = membrane - bckg_membrane;
    membrane_corr(membrane_corr<0) = 0;
        nucleus_corr = nucleus - bckg_nucleus;
        nucleus_corr(nucleus_corr<0) = 0;
            sensor_corr = sensor - bckg_sensor;
            sensor_corr(sensor_corr<0) = 0;        
%             
    s = regionprops3(sgm_nuc,'Centroid','Solidity','Centroid', ...
        'EigenValues','EigenVectors','Orientation','EquivDiameter','PrincipalAxisLength', ...
        'SurfaceArea','Volume','VoxelList');
    
    % super structure  
    x = s.Centroid;
    p = x(:,[2 1 3]'); % permute x and y
    n_nuc = size(p,1);    
    sup_centre = mean(p,1);    
    supQNT = nan(n_nuc,5);            
    distances_from_sup_centre = vecnorm((p-sup_centre)')';
    supQNT(:,1) = distances_from_sup_centre; % OK.. 
    try    
        DT = delaunayTriangulation(p); 
        FF = freeBoundary(DT); % boundary factets        
        e = DT.edges;
        % Distances of the edges for weights
        dists = vecnorm((p(e(:,1),:) - p(e(:,2),:))');
        % create Graph
        G = graph(e(:,1), e(:,2), dists, table((1:n_nuc)'));        
        %
    for n = 1:n_nuc
        node = findnode(G,n);
        supQNT(n,2) = degree(G,node); % number of neighbours
        edges = outedges(G,node); % 
        dist = G.Edges.Weight(edges);
        supQNT(n,3) = mean(dist); % average distance to neighbour
        supQNT(n,4) = min(dist);% minimal distance to neighbour
        supQNT(n,5) = isempty(intersect(FF,node)); % is internal?
    end
    %
    catch
        disp('error when trying to quantify super structure');
    end    
    if 2==n_nuc
        d = norm(p(1,:)-p(2,:));
        supQNT(1,3) = d; % mean distance to neighbour
        supQNT(1,4) = d; % minimal distance to neighbour
        supQNT(1,5) = 0;
            supQNT(2,3) = d; % mean distance to neighbour
            supQNT(2,4) = d; % minimal distance to neighbourphospho6
            supQNT(2,5) = 0;
                supQNT(:,2) = [1 1]';
    elseif 3==n_nuc
        x1 = p(1,:);
        x2 = p(2,:);
        x3 = p(3,:);
        % 1
        dstnces = [norm(x1-x2) norm(x1-x3)];
        supQNT(1,3) = mean(dstnces);
        supQNT(1,4) = min(dstnces);
        supQNT(1,5) = 0;
        % 2
        dstnces = [norm(x2-x1) norm(x2-x3)];
        supQNT(2,3) = mean(dstnces);
        supQNT(2,4) = min(dstnces);
        supQNT(2,5) = 0;
        % 3
        dstnces = [norm(x3-x1) norm(x3-x2)];
        supQNT(3,3) = mean(dstnces);
        supQNT(3,4) = min(dstnces);
        supQNT(3,5) = 0;        
                supQNT(:,2) = [2 2 2]';        
    end
    %    
    % super structure            
    try
        quantify_set_of_points([output_dir filesep fov_token '_spatial.csv'],fov_token,p);
    catch err
        disp('error when trying to quantify set of points');
        disp(err.message);
    end

disp(['super-structure quantification - done, processing time [min] ' num2str(toc/60)]);

% quantification

    data = [];
    
    for k=1:n_nuc                 
            N_k = -123456789.;
            V_k = 123456789.;
            A_k = 123456789.;
            sphericity_k = 123456789.;
            EquivDiameter_k = 123456789.;
            Solidity_k = 123456789.;
            Rg_k = 123456789.;        
            PrincipalAxisLengthRatio_1_k = 123456789.;
            PrincipalAxisLengthRatio_2_k = 123456789.;
            Oblateness_k = 123456789.;
            %
            pk = s.VoxelList{k};
            x = pk(:,1);
            y = pk(:,2);
            z = pk(:,3);
            N_k = length(x);
            shp = alphaShape(x,y,z);
            A_k = surfaceArea(shp);
            V_k = volume(shp);
            K = (4/3*pi)^(2/3)/(4*pi);
            shape_factor_k = K*A_k/(V_k^(2/3));
            Rc_k = s.Centroid(k,:);
            Rg_k = GyrationRadius(x,y,z,Rc_k(1),Rc_k(2),Rc_k(3));
            %                 
            EquivDiameter_k = s.EquivDiameter(k);
            Solidity_k = s.Solidity(k);        
            %
            L = s.PrincipalAxisLength(k,:); % decreasing
            PrincipalAxisLengthRatio_1_k = L(2)/L(1);
            PrincipalAxisLengthRatio_2_k = L(3)/L(1);        
            Oblateness_k = L(3)/mean(L(1:2));
            Ellipticity_k = L(1)/mean(L(2:3));
            %
            N_k_collar = sum(sgm_collars==k,'All');
            %
            sample = sensor_corr(sgm_nuc==k); 
            [~,Mean_nuc_sensor, Std_nuc_sensor, Skewness_nuc_sensor, Kurtosis_nuc_sensor, ...
                q_25_nuc_sensor,q_50_nuc_sensor,q_75_nuc_sensor] = get_stats(sample(:));
            sample = sensor_corr(sgm_collars==k); 
            [~,Mean_collar_sensor, Std_collar_sensor, Skewness_collar_sensor, Kurtosis_collar_sensor, ...
                q_25_collar_sensor,q_50_collar_sensor,q_75_collar_sensor] = get_stats(sample(:));
            %
            sample = nucleus_corr(sgm_nuc==k); 
            [~,Mean_nuc_nucleus, Std_nuc_nucleus, Skewness_nuc_nucleus, Kurtosis_nuc_nucleus, ...
                q_25_nuc_nucleus,q_50_nuc_nucleus,q_75_nuc_nucleus] = get_stats(sample(:));
            sample = nucleus_corr(sgm_collars==k); 
            [~,Mean_collar_nucleus, Std_collar_nucleus, Skewness_collar_nucleus, Kurtosis_collar_nucleus, ...
                q_25_collar_nucleus,q_50_collar_nucleus,q_75_collar_nucleus] = get_stats(sample(:));
            %
            sample = membrane_corr(sgm_nuc==k); 
            [~,Mean_nuc_membrane, Std_nuc_membrane, Skewness_nuc_membrane, Kurtosis_nuc_membrane, ...
                q_25_nuc_membrane,q_50_nuc_membrane,q_75_nuc_membrane] = get_stats(sample(:));
            sample = membrane_corr(sgm_collars==k); 
            [~,Mean_collar_membrane, Std_collar_membrane, Skewness_collar_membrane, Kurtosis_collar_membrane, ...
                q_25_collar_membrane,q_50_collar_membrane,q_75_collar_membrane] = get_stats(sample(:));

            rec_k = {fov_token,...
                    k,...
                    N_k,...
                    A_k,...
                    V_k,...
                    shape_factor_k,...
                    Rc_k(2),Rc_k(1),Rc_k(3), ...  
                    Rg_k,...
                    EquivDiameter_k,...
                    Solidity_k,...
                    PrincipalAxisLengthRatio_1_k,...
                    PrincipalAxisLengthRatio_2_k,...
                    Ellipticity_k, ...
                    Oblateness_k, ...
                    N_k_collar, ...
                    supQNT(k,1), ...  % distance_from_sup_centre
                    supQNT(k,2), ...  % number_of_neighbours
                    supQNT(k,3), ...  % average_distance_to_neighbour 
                    supQNT(k,4), ...  % minimal_distance_to_neighbour
                    supQNT(k,5), ...  % is_internal                                                                                
                    Mean_nuc_sensor, Std_nuc_sensor, Skewness_nuc_sensor, Kurtosis_nuc_sensor, ...
                        q_25_nuc_sensor,q_50_nuc_sensor,q_75_nuc_sensor, ...
                    Mean_collar_sensor, Std_collar_sensor, Skewness_collar_sensor, Kurtosis_collar_sensor, ...
                        q_25_collar_sensor,q_50_collar_sensor,q_75_collar_sensor, ...
                    Mean_nuc_nucleus, Std_nuc_nucleus, Skewness_nuc_nucleus, Kurtosis_nuc_nucleus, ...
                        q_25_nuc_nucleus,q_50_nuc_nucleus,q_75_nuc_nucleus, ...
                    Mean_collar_nucleus, Std_collar_nucleus, Skewness_collar_nucleus, Kurtosis_collar_nucleus, ...
                        q_25_collar_nucleus,q_50_collar_nucleus,q_75_collar_nucleus, ...                    
                    Mean_nuc_membrane, Std_nuc_membrane, Skewness_nuc_membrane, Kurtosis_nuc_membrane, ...
                        q_25_nuc_membrane,q_50_nuc_membrane,q_75_nuc_membrane, ...
                    Mean_collar_membrane, Std_collar_membrane, Skewness_collar_membrane, Kurtosis_collar_membrane, ...
                        q_25_collar_membrane,q_50_collar_membrane,q_75_collar_membrane, ... 
                        q_50_collar_sensor/(q_50_collar_sensor+q_50_nuc_sensor), ...
                        q_50_collar_membrane/(q_50_collar_membrane+q_50_nuc_membrane), ...
                        q_50_collar_nucleus/(q_50_collar_nucleus+q_50_nuc_nucleus) ...                        
                };
            
            k
            data = [ data; rec_k];                         
    end            
            caption = {'filename',...
                    'index',...
                    'N_voxels',...
                    'Area',...
                    'Volume',...
                    'shape_factor',...
                    'Xc','Yc','Zc', ...  
                    'Rg',...
                    'EquivDiameter',...
                    'Solidity',...
                    'PrincipalAxisLengthRatio_1',...
                    'PrincipalAxisLengthRatio_2',...
                    'Ellipticity', ...
                    'Oblateness', ...
                    'N_voxels_collar', ...
                    'distance_from_sup_centre',...
                    'number_of_neighbours',...
                    'average_distance_to_neighbour',...
                    'minimal_distance_to_neighbour',...
                    'is_internal'... 
                    'Mean_nuc_sensor', 'Std_nuc_sensor', 'Skewness_nuc_sensor', 'Kurtosis_nuc_sensor', ...
                        'q_25_nuc_sensor','q_50_nuc_sensor','q_75_nuc_sensor', ...
                    'Mean_collar_sensor', 'Std_collar_sensor', 'Skewness_collar_sensor', 'Kurtosis_collar_sensor', ...
                        'q_25_collar_sensor','q_50_collar_sensor','q_75_collar_sensor', ...
                    'Mean_nuc_nucleus', 'Std_nuc_nucleus', 'Skewness_nuc_nucleus', 'Kurtosis_nuc_nucleus', ...
                        'q_25_nuc_nucleus','q_50_nuc_nucleus','q_75_nuc_nucleus', ...
                    'Mean_collar_nucleus', 'Std_collar_nucleus', 'Skewness_collar_nucleus', 'Kurtosis_collar_nucleus', ...
                        'q_25_collar_nucleus','q_50_collar_nucleus','q_75_collar_nucleus', ...                    
                    'Mean_nuc_membrane', 'Std_nuc_membrane', 'Skewness_nuc_membrane', 'Kurtosis_nuc_membrane', ...
                        'q_25_nuc_membrane','q_50_nuc_membrane','q_75_nuc_membrane', ...
                    'Mean_collar_membrane', 'Std_collar_membrane', 'Skewness_collar_membrane', 'Kurtosis_collar_membrane', ...
                        'q_25_collar_membrane','q_50_collar_membrane','q_75_collar_membrane', ... 
                        'cyt_nuc_ratio_sensor','cyt_nuc_ratio_membrane','cyt_nuc_ratio_nucleus' ...
                    };

        data = [caption; data];
        
    %xlwrite([output_dir filesep fov_token '.xls'],data);
    cell2csv([output_dir filesep fov_token '.csv'],data);

    v = zeros(sx,sy,5,sz,1,'single');
    v(:,:,1,:,1) = nucleus;
    v(:,:,2,:,1) = sensor;
    v(:,:,3,:,1) = membrane;
    v(:,:,4,:,1) = sgm_nuc;
    v(:,:,5,:,1) = sgm_collars;
       
disp('quantification - done');        
    
    savename = [output_dir filesep fov_token '_sgm.ome.tif'];
    bfsave(uint16(v),savename,'dimensionOrder', 'XYCZT', 'Compression', 'LZW');   

disp(['saving - done, processing time [min] ' num2str(toc/60)]);      
   
end  

