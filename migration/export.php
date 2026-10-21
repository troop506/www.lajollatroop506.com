<?php
/*
 * Dump the WordPress site as JSON for wp2hugo.py. Run inside the WordPress
 * container:  wp eval-file export.php > export.json
 */

$home = untrailingslashit( home_url() );
$rel  = function ( $url ) use ( $home ) {
	return str_replace( $home, '', $url );
};

$items = array();
$q = new WP_Query( array(
	'post_type'      => array( 'post', 'page' ),
	'post_status'    => array( 'publish', 'private', 'draft' ),
	'posts_per_page' => -1,
	'orderby'        => 'date',
	'order'          => 'DESC',
) );
foreach ( $q->posts as $p ) {
	setup_postdata( $GLOBALS['post'] = $p );
	$thumb_id = get_post_thumbnail_id( $p );
	$items[] = array(
		'id'         => $p->ID,
		'type'       => $p->post_type,
		'status'     => $p->post_status,
		'slug'       => $p->post_name,
		'title'      => get_the_title( $p ),
		'date'       => $p->post_date,
		'modified'   => $p->post_modified,
		'author'     => get_the_author_meta( 'display_name', $p->post_author ),
		'path'       => $rel( get_permalink( $p ) ),
		'parent'     => $p->post_parent,
		'menu_order' => $p->menu_order,
		'template'   => get_page_template_slug( $p ),
		'excerpt'    => $p->post_excerpt,
		'categories' => wp_list_pluck( get_the_category( $p->ID ), 'slug' ),
		'tags'       => wp_list_pluck( get_the_tags( $p->ID ) ?: array(), 'name' ),
		'thumbnail'  => $thumb_id ? $rel( wp_get_attachment_url( $thumb_id ) ) : null,
		'thumb_alt'  => $thumb_id ? get_post_meta( $thumb_id, '_wp_attachment_image_alt', true ) : null,
		'content'    => apply_filters( 'the_content', $p->post_content ),
		'raw'        => $p->post_content,
	);
}

$terms = array();
foreach ( array( 'category', 'post_tag' ) as $tax ) {
	foreach ( get_terms( array( 'taxonomy' => $tax, 'hide_empty' => false ) ) as $t ) {
		$terms[] = array( 'taxonomy' => $tax, 'slug' => $t->slug, 'name' => $t->name, 'count' => $t->count );
	}
}

$menu = array();
foreach ( wp_get_nav_menu_items( 'Header Menu' ) as $m ) {
	$menu[] = array(
		'id'     => $m->ID,
		'parent' => (int) $m->menu_item_parent,
		'title'  => $m->title,
		'url'    => $rel( $m->url ),
		'order'  => $m->menu_order,
	);
}

echo wp_json_encode( array(
	'name'        => get_bloginfo( 'name' ),
	'description' => get_bloginfo( 'description' ),
	'items'       => $items,
	'terms'       => $terms,
	'menu'        => $menu,
), JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES | JSON_UNESCAPED_UNICODE );
