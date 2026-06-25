function L = smooth_watershed(bw,sigma)

    D = bwdist(~bw);
    % smooth distance map
    D = gauss3filter(D,sigma);
    %
    D = -D;
    D(~bw) = Inf;
    L = watershed(D);
    L(~bw) = 0;
 
end

