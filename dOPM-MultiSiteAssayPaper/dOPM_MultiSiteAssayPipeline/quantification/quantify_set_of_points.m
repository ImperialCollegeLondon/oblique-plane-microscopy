function rec = quantify_set_of_points(output_fname,fov_token,p)

% p - points

    % super structure  
    n_p = size(p,1); % number of nodes!   
    sup_centre = mean(p,1);    
    supQNT = nan(n_p,5);            
    distances_from_sup_centre = vecnorm((p-sup_centre)')';
    supQNT(:,1) = distances_from_sup_centre; % OK.. 
    %
        DT = delaunayTriangulation(p); 
        [totalVolume, volumes] = Triangulation_Volume(DT);

        totalArea = 0; outer_facet_areas = 0;
        try
        [totalArea, outer_facet_areas] = Triangulation_Surface(DT);
        catch 
        end
        %
        FF = freeBoundary(DT); % boundary facets - "Free Facets"  s      
        e = DT.edges;
        % Distances of the edges for weights
        dists = vecnorm((p(e(:,1),:) - p(e(:,2),:))');
        % create Graph
        G = graph(e(:,1), e(:,2), dists, table((1:n_p)'));        
        %

    for n = 1:n_p
        node = findnode(G,n);
        supQNT(n,2) = degree(G,node); % number of neighbours
        edges = outedges(G,node); % 
        dist = G.Edges.Weight(edges);
        supQNT(n,3) = mean(dist); % average distance to neighbour
        supQNT(n,4) = min(dist);% minimal distance to neighbour
        supQNT(n,5) = isempty(intersect(FF,node)); % is internal?
    end
    %
    %repeat the same for FF and its xor?

    number_of_boundary_edges = numel(unique(FF));
    
    %
    % degree statsitics
    [~,Mean_dgree, Std_dgree, Skewness_dgree, Kurtosis_dgree, ...
       q_25_dgree,q_50_dgree,q_75_dgree] = get_stats(supQNT(:,2));
    %
    % distance from centre statistics
    [~,Mean_dsc, Std_dsc, Skewness_dsc, Kurtosis_dsc, ...
       q_25_dsc,q_50_dsc,q_75_dsc] = get_stats(supQNT(:,1));

    % edges_statistics
    [~,Mean_edg, Std_edg, Skewness_edg, Kurtosis_edg, ...
       q_25_edg,q_50_edg,q_75_edg] = get_stats(dists);

    % volumes_statistics
    [~,Mean_vlms, Std_vlms, Skewness_vlms, Kurtosis_vlms, ...
       q_25_vlms,q_50_vlms,q_75_vlms] = get_stats(volumes);

    % outer facets statistics
    [~,Mean_fct, Std_fct, Skewness_fct, Kurtosis_fct, ...
       q_25_fct,q_50_fct,q_75_fct] = get_stats(outer_facet_areas);
    
% % Visualize the triangulation
% figure;
% trisurf(DT.ConnectivityList,p(:,1),p(:,2),p(:,3));
% xlabel('X');
% ylabel('Y');
% zlabel('Z');
% title('Delaunay Triangulation');
% axis equal;    

rec = {fov_token,n_p,totalVolume,n_p/totalVolume,totalArea, number_of_boundary_edges, number_of_boundary_edges/n_p, ...
        Mean_dgree, Std_dgree, Skewness_dgree, Kurtosis_dgree, ...
       q_25_dgree,q_50_dgree,q_75_dgree, ...
    Mean_dsc, Std_dsc, Skewness_dsc, Kurtosis_dsc, ...
       q_25_dsc,q_50_dsc,q_75_dsc, ...
    Mean_edg, Std_edg, Skewness_edg, Kurtosis_edg, ...
       q_25_edg,q_50_edg,q_75_edg, ...
    Mean_vlms, Std_vlms, Skewness_vlms, Kurtosis_vlms, ...
       q_25_vlms,q_50_vlms,q_75_vlms, ...
    Mean_fct, Std_fct, Skewness_fct, Kurtosis_fct, ...
       q_25_fct,q_50_fct,q_75_fct};

caption = {'fov_token','n_p','totalVolume','n_p/totalVolume','totalArea', ...
    'number_of_boundary_edges', 'fraction_of_boundary_edges/n_p', ...
        'Mean_dgree',' Std_dgree',' Skewness_dgree',' Kurtosis_dgree', ...
       'q_25_dgree','q_50_dgree','q_75_dgree', ...
    'Mean_dsc',' Std_dsc',' Skewness_dsc',' Kurtosis_dsc', ...
       'q_25_dsc','q_50_dsc','q_75_dsc', ...
    'Mean_edg',' Std_edg',' Skewness_edg',' Kurtosis_edg', ...
       'q_25_edg','q_50_edg','q_75_edg', ...
    'Mean_vlms',' Std_vlms',' Skewness_vlms',' Kurtosis_vlms', ...
       'q_25_vlms','q_50_vlms','q_75_vlms', ...
    'Mean_fct',' Std_fct',' Skewness_fct',' Kurtosis_fct', ...
       'q_25_fct','q_50_fct','q_75_fct'};
try
    cell2csv(output_fname,[caption; rec]);
catch   
    dsip('quantify_set_of_points - saving error');
end

end